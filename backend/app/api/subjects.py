from datetime import datetime
import secrets
import string
import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo.errors import DuplicateKeyError
from typing import Optional

from app.database.collections import get_collection
from app.models.subject import (
    JoinSubjectRequest,
    SubjectCreateRequest,
    SubjectResponse,
    SubjectUpdateRequest,
)
from app.models.roster import StudentRosterItem
from app.utils.dependencies import get_current_student, get_current_teacher, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_subject(
    doc: dict, *, student_count: int | None = None, task_count: int | None = None
) -> SubjectResponse:
    return SubjectResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        code=doc.get("code"),
        teacher_uid=doc["teacher_uid"],
        join_code=doc["join_code"],
        student_count=student_count,
        task_count=task_count,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _generate_join_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _find_subject_or_404(subject_id: str) -> dict:
    if not ObjectId.is_valid(subject_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")

    subjects_collection = get_collection("subjects")
    subject = await subjects_collection.find_one({"_id": ObjectId(subject_id)})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    request: SubjectCreateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    """
    Create a new subject (teachers only)

    Generates a unique join code for student enrollment.
    Subject name is required, code is optional.
    """
    try:
        subjects_collection = get_collection("subjects")

        # Generate unique join code
        join_code = _generate_join_code()
        for attempt in range(5):
            existing = await subjects_collection.find_one({"join_code": join_code})
            if not existing:
                break
            join_code = _generate_join_code()
            logger.debug(f"Join code collision, retry {attempt + 1}/5")
        else:
            logger.error(f"Failed to generate unique join code after 5 attempts for teacher: {current_teacher['uid']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate join code, please try again",
            )

        now = datetime.utcnow()
        subject_doc = {
            "name": request.name.strip(),
            "code": request.code.strip() if request.code else None,
            "teacher_uid": current_teacher["uid"],
            "join_code": join_code,
            "created_at": now,
            "updated_at": now,
        }

        result = await subjects_collection.insert_one(subject_doc)
        logger.info(f"Subject created: id={result.inserted_id}, name={request.name}, teacher={current_teacher['uid']}, join_code={join_code}")

        created = await subjects_collection.find_one({"_id": result.inserted_id})
        if not created:
            logger.error(f"Failed to retrieve created subject: id={result.inserted_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subject creation failed"
            )

        return _serialize_subject(created)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subject creation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subject"
        )


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(current_user: dict = Depends(get_current_user)):
    subjects_collection = get_collection("subjects")

    if current_user.get("role") == "teacher":
        cursor = subjects_collection.find({"teacher_uid": current_user["uid"]}).sort(
            [("updated_at", -1), ("_id", -1)]
        )
        subjects = await cursor.to_list(length=None)
        subject_oids = [s.get("_id") for s in subjects if s.get("_id")]
        subject_oids = [s for s in subject_oids if isinstance(s, ObjectId)]

        student_counts: dict[ObjectId, int] = {}
        task_counts: dict[ObjectId, int] = {}
        if subject_oids:
            enrollments_collection = get_collection("enrollments")
            enrollment_agg = await enrollments_collection.aggregate(
                [
                    {"$match": {"subject_id": {"$in": subject_oids}}},
                    {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}},
                ]
            ).to_list(length=None)
            for row in enrollment_agg:
                if not isinstance(row, dict):
                    continue
                sid = row.get("_id")
                if isinstance(sid, ObjectId):
                    student_counts[sid] = int(row.get("count") or 0)

            tasks_collection = get_collection("tasks")
            task_agg = await tasks_collection.aggregate(
                [
                    {"$match": {"subject_id": {"$in": subject_oids}}},
                    {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}},
                ]
            ).to_list(length=None)
            for row in task_agg:
                if not isinstance(row, dict):
                    continue
                sid = row.get("_id")
                if isinstance(sid, ObjectId):
                    task_counts[sid] = int(row.get("count") or 0)

        return [
            _serialize_subject(
                s,
                student_count=student_counts.get(s.get("_id"), 0),
                task_count=task_counts.get(s.get("_id"), 0),
            )
            for s in subjects
        ]

    enrollments_collection = get_collection("enrollments")
    enrollments = await enrollments_collection.find({"student_uid": current_user["uid"]}).to_list(
        length=None
    )
    subject_ids = [e["subject_id"] for e in enrollments if e.get("subject_id")]
    if not subject_ids:
        return []

    cursor = subjects_collection.find({"_id": {"$in": subject_ids}}).sort(
        [("updated_at", -1), ("_id", -1)]
    )
    subjects = await cursor.to_list(length=None)
    return [_serialize_subject(s) for s in subjects]


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: str, current_user: dict = Depends(get_current_user)):
    subject = await _find_subject_or_404(subject_id)

    if current_user.get("role") == "teacher":
        if subject["teacher_uid"] != current_user["uid"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return _serialize_subject(subject)

    enrollments_collection = get_collection("enrollments")
    enrollment = await enrollments_collection.find_one(
        {"subject_id": subject["_id"], "student_uid": current_user["uid"]}
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _serialize_subject(subject)


@router.get("/{subject_id}/roster", response_model=list[StudentRosterItem])
async def get_subject_roster(subject_id: str, current_teacher: dict = Depends(get_current_teacher)):
    subject = await _find_subject_or_404(subject_id)
    if subject["teacher_uid"] != current_teacher["uid"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    enrollments_collection = get_collection("enrollments")
    enrollments = await (
        enrollments_collection.find({"subject_id": subject["_id"]})
        .sort([("enrolled_at", -1), ("_id", -1)])
        .to_list(length=None)
    )

    student_uids = [e.get("student_uid") for e in enrollments if e.get("student_uid")]
    users_by_uid = {}
    if student_uids:
        users_collection = get_collection("users")
        users = await users_collection.find({"uid": {"$in": student_uids}}).to_list(length=None)
        users_by_uid = {u.get("uid"): u for u in users if u.get("uid")}

    roster: list[StudentRosterItem] = []
    for e in enrollments:
        uid = e.get("student_uid")
        if not uid:
            continue
        user = users_by_uid.get(uid) or {}
        roster.append(
            StudentRosterItem(
                uid=uid,
                name=user.get("name"),
                email=user.get("email"),
                enrolled_at=e.get("enrolled_at"),
            )
        )

    return roster


@router.post("/join", response_model=SubjectResponse)
async def join_subject(
    request: JoinSubjectRequest,
    current_student: dict = Depends(get_current_student),
):
    subjects_collection = get_collection("subjects")
    enrollments_collection = get_collection("enrollments")

    join_code = request.join_code.strip().upper()
    subject = await subjects_collection.find_one({"join_code": join_code})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid join code")

    now = datetime.utcnow()
    enrollment_doc = {
        "subject_id": subject["_id"],
        "student_uid": current_student["uid"],
        "enrolled_at": now,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await enrollments_collection.insert_one(enrollment_doc)
    except DuplicateKeyError:
        pass

    return _serialize_subject(subject)


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    request: SubjectUpdateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    subject = await _find_subject_or_404(subject_id)
    if subject["teacher_uid"] != current_teacher["uid"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update: dict = {"updated_at": datetime.utcnow()}
    if request.name is not None:
        update["name"] = request.name.strip()
    if request.code is not None:
        update["code"] = request.code.strip() if request.code else None

    subjects_collection = get_collection("subjects")
    await subjects_collection.update_one({"_id": subject["_id"]}, {"$set": update})
    updated = await subjects_collection.find_one({"_id": subject["_id"]})
    return _serialize_subject(updated)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(subject_id: str, current_teacher: dict = Depends(get_current_teacher)):
    subject = await _find_subject_or_404(subject_id)
    if subject["teacher_uid"] != current_teacher["uid"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    enrollments_collection = get_collection("enrollments")
    await enrollments_collection.delete_many({"subject_id": subject["_id"]})

    subjects_collection = get_collection("subjects")
    await subjects_collection.delete_one({"_id": subject["_id"]})


@router.get("/health")
async def health():
    return {"status": "ok", "service": "subjects"}
