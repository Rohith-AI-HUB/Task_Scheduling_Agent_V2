from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.collections import get_collection
from app.models.task import (
    TaskCreateRequest,
    TaskEvaluationsSummaryResponse,
    TaskResponse,
    TaskUpdateRequest,
)
from app.utils.dependencies import get_current_teacher, get_current_user

router = APIRouter()


def _serialize_task(doc: dict) -> TaskResponse:
    return TaskResponse(
        id=str(doc["_id"]),
        subject_id=str(doc["subject_id"]),
        title=doc["title"],
        description=doc.get("description"),
        deadline=doc.get("deadline"),
        points=doc.get("points"),
        task_type=doc.get("task_type"),
        type=doc.get("type", "individual"),
        problem_statements=list(doc.get("problem_statements") or []),
        group_settings=doc.get("group_settings"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _find_task_or_404(task_id: str) -> dict:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    tasks_collection = get_collection("tasks")
    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _ensure_teacher_owns_subject(teacher_uid: str, subject_oid: ObjectId) -> dict:
    subjects_collection = get_collection("subjects")
    subject = await subjects_collection.find_one({"_id": subject_oid})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if subject.get("teacher_uid") != teacher_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return subject


async def _ensure_student_enrolled(student_uid: str, subject_oid: ObjectId) -> None:
    enrollments_collection = get_collection("enrollments")
    enrollment = await enrollments_collection.find_one(
        {"subject_id": subject_oid, "student_uid": student_uid}
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    if not ObjectId.is_valid(request.subject_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")

    subject_oid = ObjectId(request.subject_id)
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    now = datetime.utcnow()
    normalized_problem_statements = [
        s.strip() for s in (request.problem_statements or []) if isinstance(s, str) and s.strip()
    ]
    task_doc = {
        "subject_id": subject_oid,
        "title": request.title.strip(),
        "description": request.description.strip() if request.description else None,
        "deadline": request.deadline,
        "points": request.points,
        "task_type": request.task_type.strip() if request.task_type else None,
        "type": request.type,
        "problem_statements": normalized_problem_statements if request.type == "group" else [],
        "group_settings": request.group_settings.model_dump() if request.type == "group" and request.group_settings else None,
        "created_at": now,
        "updated_at": now,
    }
    if request.type == "group" and not request.group_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_settings is required for group tasks",
        )

    tasks_collection = get_collection("tasks")
    result = await tasks_collection.insert_one(task_doc)
    created = await tasks_collection.find_one({"_id": result.inserted_id})
    return _serialize_task(created)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    subject_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    tasks_collection = get_collection("tasks")
    subjects_collection = get_collection("subjects")

    if subject_id is not None:
        if not ObjectId.is_valid(subject_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")
        subject_oid = ObjectId(subject_id)

        if current_user.get("role") == "teacher":
            await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
        else:
            await _ensure_student_enrolled(current_user["uid"], subject_oid)

        tasks = await (
            tasks_collection.find({"subject_id": subject_oid})
            .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
            .to_list(length=None)
        )
        return [_serialize_task(t) for t in tasks]

    if current_user.get("role") == "teacher":
        subjects = await subjects_collection.find({"teacher_uid": current_user["uid"]}).to_list(
            length=None
        )
        subject_oids = [s["_id"] for s in subjects if s.get("_id")]
        if not subject_oids:
            return []
        tasks = await (
            tasks_collection.find({"subject_id": {"$in": subject_oids}})
            .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
            .to_list(length=None)
        )
        return [_serialize_task(t) for t in tasks]

    enrollments_collection = get_collection("enrollments")
    enrollments = await enrollments_collection.find({"student_uid": current_user["uid"]}).to_list(
        length=None
    )
    subject_oids = [e["subject_id"] for e in enrollments if e.get("subject_id")]
    if not subject_oids:
        return []
    tasks = await (
        tasks_collection.find({"subject_id": {"$in": subject_oids}})
        .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
        .to_list(length=None)
    )
    return [_serialize_task(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]

    if current_user.get("role") == "teacher":
        await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
        return _serialize_task(task)

    await _ensure_student_enrolled(current_user["uid"], subject_oid)
    return _serialize_task(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    update: dict = {"updated_at": datetime.utcnow()}
    if request.title is not None:
        update["title"] = request.title.strip()
    if request.description is not None:
        update["description"] = request.description.strip() if request.description else None
    if request.deadline is not None:
        update["deadline"] = request.deadline
    if request.points is not None:
        update["points"] = request.points
    if request.task_type is not None:
        update["task_type"] = request.task_type.strip() if request.task_type else None
    if request.type is not None:
        update["type"] = request.type
        if request.type != "group":
            update["problem_statements"] = []
            update["group_settings"] = None
    if request.problem_statements is not None:
        update["problem_statements"] = [
            s.strip()
            for s in (request.problem_statements or [])
            if isinstance(s, str) and s.strip()
        ]
    if request.group_settings is not None:
        update["group_settings"] = request.group_settings.model_dump()

    tasks_collection = get_collection("tasks")
    await tasks_collection.update_one({"_id": task["_id"]}, {"$set": update})
    updated = await tasks_collection.find_one({"_id": task["_id"]})
    return _serialize_task(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, current_teacher: dict = Depends(get_current_teacher)):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    tasks_collection = get_collection("tasks")
    await tasks_collection.delete_one({"_id": task["_id"]})


@router.get("/{task_id}/evaluations/summary", response_model=TaskEvaluationsSummaryResponse)
async def get_evaluations_summary(
    task_id: str,
    current_teacher: dict = Depends(get_current_teacher),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    submissions = await submissions_collection.find({"task_id": task["_id"]}).to_list(length=None)

    status_counts: dict[str, int] = {}
    total = 0
    score_sum = 0.0
    score_count = 0

    for s in submissions:
        total += 1
        ev = s.get("evaluation") if isinstance(s.get("evaluation"), dict) else None
        st = str(ev.get("status") if ev else "pending")
        status_counts[st] = status_counts.get(st, 0) + 1
        ai_score = ev.get("ai_score") if ev else None
        if isinstance(ai_score, (int, float)):
            score_sum += float(ai_score)
            score_count += 1

    avg = (score_sum / score_count) if score_count else None
    return TaskEvaluationsSummaryResponse(
        task_id=task_id,
        total_submissions=total,
        status_counts=status_counts,
        average_ai_score=avg,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tasks"}
