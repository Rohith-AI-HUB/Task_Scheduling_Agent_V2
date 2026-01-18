from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status

from app.ai.group_maker import make_groups
from app.database.collections import get_collection


def _now() -> datetime:
    return datetime.utcnow()


async def _find_task_or_404(task_oid: ObjectId) -> dict:
    tasks_collection = get_collection("tasks")
    task = await tasks_collection.find_one({"_id": task_oid})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _ensure_teacher_owns_subject(teacher_uid: str, subject_oid: ObjectId) -> None:
    subjects_collection = get_collection("subjects")
    subject = await subjects_collection.find_one({"_id": subject_oid})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if subject.get("teacher_uid") != teacher_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def _ensure_student_enrolled(student_uid: str, subject_oid: ObjectId) -> None:
    enrollments_collection = get_collection("enrollments")
    enrollment = await enrollments_collection.find_one(
        {"subject_id": subject_oid, "student_uid": student_uid}
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def serialize_group(doc: dict, *, submission: dict | None = None) -> dict:
    payload = {
        "id": str(doc["_id"]),
        "task_id": str(doc["task_id"]),
        "subject_id": str(doc["subject_id"]),
        "group_set_id": str(doc["group_set_id"]),
        "name": doc.get("name") or "",
        "member_uids": list(doc.get("member_uids") or []),
        "assigned_problem_index": doc.get("assigned_problem_index"),
        "assigned_problem_statement": doc.get("assigned_problem_statement"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }
    if submission:
        payload.update(
            {
                "submission_id": str(submission.get("_id")),
                "submitted_at": submission.get("submitted_at"),
                "submission_updated_at": submission.get("updated_at"),
                "submitted_by_uid": submission.get("student_uid"),
            }
        )
    return payload


async def generate_groups_for_task(
    *,
    task_id: str,
    teacher_uid: str,
    regenerate: bool = False,
) -> tuple[dict, list[dict], bool]:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(teacher_uid, subject_oid)

    if task.get("type") != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Groups can only be generated for group tasks",
        )

    group_sets_collection = get_collection("group_sets")
    groups_collection = get_collection("groups")
    submissions_collection = get_collection("submissions")

    existing_set = await group_sets_collection.find_one({"task_id": task_oid})
    if existing_set and not regenerate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Groups already exist for this task",
        )

    if existing_set and regenerate:
        has_submissions = (
            await submissions_collection.find_one({"task_id": task_oid}) is not None
        )
        if has_submissions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot regenerate groups after submissions exist",
            )
        await groups_collection.delete_many({"group_set_id": existing_set["_id"]})
        await group_sets_collection.delete_one({"_id": existing_set["_id"]})

    group_settings = task.get("group_settings") or {}
    group_size = int(group_settings.get("group_size") or 0)
    if group_size < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task group_settings.group_size must be at least 2",
        )

    enrollments_collection = get_collection("enrollments")
    enrollments = await (
        enrollments_collection.find({"subject_id": subject_oid})
        .sort([("enrolled_at", 1), ("_id", 1)])
        .to_list(length=None)
    )
    student_uids = [
        e.get("student_uid")
        for e in enrollments
        if isinstance(e, dict) and e.get("student_uid")
    ]

    problems = list(task.get("problem_statements") or [])
    made = make_groups(
        student_uids=student_uids,
        group_size=group_size,
        problem_statements=problems,
    )

    now = _now()
    group_set_doc = {
        "task_id": task_oid,
        "subject_id": subject_oid,
        "group_settings": group_settings,
        "problem_statements": problems,
        "created_at": now,
        "updated_at": now,
    }
    set_result = await group_sets_collection.insert_one(group_set_doc)
    group_set_doc["_id"] = set_result.inserted_id

    group_docs: list[dict] = []
    for i, g in enumerate(made, start=1):
        group_docs.append(
            {
                "task_id": task_oid,
                "subject_id": subject_oid,
                "group_set_id": set_result.inserted_id,
                "name": f"Group {i}",
                "member_uids": list(g.member_uids),
                "assigned_problem_index": g.assigned_problem_index,
                "assigned_problem_statement": g.assigned_problem_statement,
                "created_at": now,
                "updated_at": now,
            }
        )

    if group_docs:
        await groups_collection.insert_many(group_docs)

    created_groups = await (
        groups_collection.find({"group_set_id": set_result.inserted_id})
        .sort([("name", 1), ("_id", 1)])
        .to_list(length=None)
    )
    return group_set_doc, created_groups, False


async def list_groups_for_task(*, task_id: str, user: dict) -> tuple[dict | None, list[dict], bool]:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]

    if user.get("role") == "teacher":
        await _ensure_teacher_owns_subject(user["uid"], subject_oid)
    else:
        await _ensure_student_enrolled(user["uid"], subject_oid)

    group_sets_collection = get_collection("group_sets")
    groups_collection = get_collection("groups")
    submissions_collection = get_collection("submissions")

    group_set = await group_sets_collection.find_one({"task_id": task_oid})
    if not group_set:
        has_submissions = (await submissions_collection.find_one({"task_id": task_oid})) is not None
        return None, [], has_submissions

    groups = await (
        groups_collection.find({"group_set_id": group_set["_id"]})
        .sort([("name", 1), ("_id", 1)])
        .to_list(length=None)
    )

    has_submissions = (await submissions_collection.find_one({"task_id": task_oid})) is not None
    return group_set, groups, has_submissions


async def get_student_group_for_task(*, task_id: str, student_uid: str) -> dict:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_student_enrolled(student_uid, subject_oid)

    group_sets_collection = get_collection("group_sets")
    groups_collection = get_collection("groups")

    group_set = await group_sets_collection.find_one({"task_id": task_oid})
    if not group_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groups not found")

    group = await groups_collection.find_one(
        {"group_set_id": group_set["_id"], "member_uids": student_uid}
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group
