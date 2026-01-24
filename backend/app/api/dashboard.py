from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Response

from app.database.collections import get_collection
from app.models.dashboard import (
    DueSoonItem,
    DueSoonResponse,
    TeacherPendingSummaryResponse,
    TeacherUpcomingTaskItem,
    TeacherUpcomingTasksResponse,
    UpcomingTaskItem,
    UpcomingTasksResponse,
)
from app.utils.dependencies import get_current_student, get_current_teacher

router = APIRouter()


@router.get("/due-soon", response_model=DueSoonResponse)
async def due_soon(
    response: Response,
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=5, ge=1, le=50),
    current_student: dict = Depends(get_current_student),
):
    response.headers["Cache-Control"] = "no-store"

    now = datetime.utcnow()
    end = now + timedelta(days=days)

    enrollments_collection = get_collection("enrollments")
    enrollments = await enrollments_collection.find({"student_uid": current_student["uid"]}).to_list(
        length=None
    )
    subject_oids = [e.get("subject_id") for e in enrollments if e.get("subject_id")]
    subject_oids = [s for s in subject_oids if isinstance(s, ObjectId)]
    if not subject_oids:
        return DueSoonResponse(generated_at=now, items=[])

    tasks_collection = get_collection("tasks")
    raw_tasks = await (
        tasks_collection.find(
            {"subject_id": {"$in": subject_oids}, "deadline": {"$ne": None, "$lte": end}}
        )
        .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
        .to_list(length=5000)
    )
    task_ids = [t.get("_id") for t in raw_tasks if t.get("_id")]
    task_ids = [t for t in task_ids if isinstance(t, ObjectId)]
    if not task_ids:
        return DueSoonResponse(generated_at=now, items=[])

    submissions_collection = get_collection("submissions")
    submitted_task_ids: set[ObjectId] = set()

    individual_subs = await submissions_collection.find(
        {"task_id": {"$in": task_ids}, "student_uid": current_student["uid"], "group_id": None}
    ).to_list(length=None)
    for s in individual_subs:
        tid = s.get("task_id")
        if isinstance(tid, ObjectId):
            submitted_task_ids.add(tid)

    groups_collection = get_collection("groups")
    group_docs = await groups_collection.find(
        {"task_id": {"$in": task_ids}, "member_uids": current_student["uid"]}
    ).to_list(length=None)
    group_ids = [g.get("_id") for g in group_docs if g.get("_id")]
    group_ids = [g for g in group_ids if isinstance(g, ObjectId)]
    if group_ids:
        group_subs = await submissions_collection.find(
            {"task_id": {"$in": task_ids}, "group_id": {"$in": group_ids}}
        ).to_list(length=None)
        for s in group_subs:
            tid = s.get("task_id")
            if isinstance(tid, ObjectId):
                submitted_task_ids.add(tid)

    items: list[DueSoonItem] = []
    for t in raw_tasks:
        tid = t.get("_id")
        if not isinstance(tid, ObjectId) or tid in submitted_task_ids:
            continue
        deadline = t.get("deadline")
        if not isinstance(deadline, datetime):
            continue

        delta_min = int((deadline - now).total_seconds() // 60)
        is_overdue = deadline < now
        if is_overdue or deadline <= now + timedelta(days=2):
            band = "urgent"
        elif deadline <= now + timedelta(days=7):
            band = "high"
        else:
            band = "normal"

        items.append(
            DueSoonItem(
                task_id=str(tid),
                subject_id=str(t.get("subject_id")),
                title=str(t.get("title") or "Task"),
                deadline=deadline,
                band=band,
                due_in_minutes=delta_min,
                is_overdue=is_overdue,
            )
        )
        if len(items) >= limit:
            break

    return DueSoonResponse(generated_at=now, items=items)


@router.get("/upcoming", response_model=UpcomingTasksResponse)
async def upcoming(
    response: Response,
    days: int = Query(default=14, ge=1, le=60),
    limit: int = Query(default=8, ge=1, le=50),
    current_student: dict = Depends(get_current_student),
):
    response.headers["Cache-Control"] = "no-store"

    now = datetime.utcnow()
    end = now + timedelta(days=days)

    enrollments_collection = get_collection("enrollments")
    enrollments = await enrollments_collection.find({"student_uid": current_student["uid"]}).to_list(
        length=None
    )
    subject_oids = [e.get("subject_id") for e in enrollments if e.get("subject_id")]
    subject_oids = [s for s in subject_oids if isinstance(s, ObjectId)]
    if not subject_oids:
        return UpcomingTasksResponse(generated_at=now, items=[])

    tasks_collection = get_collection("tasks")
    raw_tasks = await (
        tasks_collection.find(
            {
                "subject_id": {"$in": subject_oids},
                "deadline": {"$ne": None, "$gte": now, "$lte": end},
            }
        )
        .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
        .to_list(length=5000)
    )
    task_ids = [t.get("_id") for t in raw_tasks if t.get("_id")]
    task_ids = [t for t in task_ids if isinstance(t, ObjectId)]
    if not task_ids:
        return UpcomingTasksResponse(generated_at=now, items=[])

    submissions_collection = get_collection("submissions")
    submitted_task_ids: set[ObjectId] = set()

    individual_subs = await submissions_collection.find(
        {"task_id": {"$in": task_ids}, "student_uid": current_student["uid"], "group_id": None}
    ).to_list(length=None)
    for s in individual_subs:
        tid = s.get("task_id")
        if isinstance(tid, ObjectId):
            submitted_task_ids.add(tid)

    groups_collection = get_collection("groups")
    group_docs = await groups_collection.find(
        {"task_id": {"$in": task_ids}, "member_uids": current_student["uid"]}
    ).to_list(length=None)
    group_ids = [g.get("_id") for g in group_docs if g.get("_id")]
    group_ids = [g for g in group_ids if isinstance(g, ObjectId)]
    if group_ids:
        group_subs = await submissions_collection.find(
            {"task_id": {"$in": task_ids}, "group_id": {"$in": group_ids}}
        ).to_list(length=None)
        for s in group_subs:
            tid = s.get("task_id")
            if isinstance(tid, ObjectId):
                submitted_task_ids.add(tid)

    items: list[UpcomingTaskItem] = []
    for t in raw_tasks:
        tid = t.get("_id")
        if not isinstance(tid, ObjectId) or tid in submitted_task_ids:
            continue
        deadline = t.get("deadline")
        if not isinstance(deadline, datetime):
            continue

        delta_min = int((deadline - now).total_seconds() // 60)
        if deadline <= now + timedelta(days=2):
            band = "urgent"
        elif deadline <= now + timedelta(days=7):
            band = "high"
        else:
            band = "normal"

        items.append(
            UpcomingTaskItem(
                task_id=str(tid),
                subject_id=str(t.get("subject_id")),
                title=str(t.get("title") or "Task"),
                deadline=deadline,
                band=band,
                due_in_minutes=delta_min,
            )
        )
        if len(items) >= limit:
            break

    return UpcomingTasksResponse(generated_at=now, items=items)


@router.get("/teacher/upcoming", response_model=TeacherUpcomingTasksResponse)
async def teacher_upcoming(
    response: Response,
    days: int = Query(default=14, ge=1, le=60),
    limit: int = Query(default=8, ge=1, le=50),
    current_teacher: dict = Depends(get_current_teacher),
):
    response.headers["Cache-Control"] = "no-store"

    now = datetime.utcnow()
    end = now + timedelta(days=days)

    subjects_collection = get_collection("subjects")
    subjects = await subjects_collection.find({"teacher_uid": current_teacher["uid"]}).to_list(length=None)
    subject_oids = [s.get("_id") for s in subjects if s.get("_id")]
    subject_oids = [s for s in subject_oids if isinstance(s, ObjectId)]
    if not subject_oids:
        return TeacherUpcomingTasksResponse(generated_at=now, items=[])

    subjects_by_id = {s.get("_id"): s for s in subjects if isinstance(s.get("_id"), ObjectId)}

    tasks_collection = get_collection("tasks")
    raw_tasks = await (
        tasks_collection.find(
            {
                "subject_id": {"$in": subject_oids},
                "deadline": {"$ne": None, "$gte": now, "$lte": end},
            }
        )
        .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
        .to_list(length=5000)
    )

    items: list[TeacherUpcomingTaskItem] = []
    for t in raw_tasks:
        tid = t.get("_id")
        if not isinstance(tid, ObjectId):
            continue
        subject_id = t.get("subject_id")
        if not isinstance(subject_id, ObjectId):
            continue
        deadline = t.get("deadline")
        if not isinstance(deadline, datetime):
            continue

        due_in_minutes = int((deadline - now).total_seconds() // 60)
        if deadline <= now + timedelta(days=2):
            band = "urgent"
        elif deadline <= now + timedelta(days=7):
            band = "high"
        else:
            band = "normal"

        subject = subjects_by_id.get(subject_id) or {}
        items.append(
            TeacherUpcomingTaskItem(
                task_id=str(tid),
                subject_id=str(subject_id),
                subject_name=str(subject.get("name") or "Subject"),
                title=str(t.get("title") or "Task"),
                deadline=deadline,
                band=band,
                due_in_minutes=due_in_minutes,
            )
        )
        if len(items) >= limit:
            break

    return TeacherUpcomingTasksResponse(generated_at=now, items=items)


@router.get("/teacher/pending", response_model=TeacherPendingSummaryResponse)
async def teacher_pending(
    response: Response,
    current_teacher: dict = Depends(get_current_teacher),
):
    response.headers["Cache-Control"] = "no-store"

    now = datetime.utcnow()

    subjects_collection = get_collection("subjects")
    subjects = await subjects_collection.find({"teacher_uid": current_teacher["uid"]}).to_list(length=None)
    subject_oids = [s.get("_id") for s in subjects if s.get("_id")]
    subject_oids = [s for s in subject_oids if isinstance(s, ObjectId)]
    if not subject_oids:
        return TeacherPendingSummaryResponse(generated_at=now, pending_submissions=0, total_submissions=0)

    submissions_collection = get_collection("submissions")
    total = await submissions_collection.count_documents({"subject_id": {"$in": subject_oids}})
    pending = await submissions_collection.count_documents(
        {"subject_id": {"$in": subject_oids}, "score": None}
    )

    return TeacherPendingSummaryResponse(
        generated_at=now,
        pending_submissions=int(pending or 0),
        total_submissions=int(total or 0),
    )
