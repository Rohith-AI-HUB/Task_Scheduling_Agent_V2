from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from bson import ObjectId

from app.ai.task_scheduler import TaskScheduler
from app.models.context import TaskCompletionPattern, UserContext


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    async def to_list(self, *, length=None):
        return list(self._docs)


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def find(self, query: dict):
        def match(doc: dict) -> bool:
            for k, v in query.items():
                if isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        return False
                else:
                    if doc.get(k) != v:
                        return False
            return True

        return _FakeCursor([d for d in self._docs if match(d)])


class _FakeContextManager:
    def __init__(self, *, context: UserContext, workload: dict):
        self._context = context
        self._workload = workload

    async def get_user_context(self, user_uid: str):
        return self._context

    async def get_workload(self, user_uid: str):
        return self._workload


@pytest.mark.asyncio
async def test_generate_schedule_orders_by_priority(monkeypatch):
    user_uid = "student-1"
    subject_id = ObjectId()
    now = datetime.utcnow()

    t1_id = ObjectId()
    t2_id = ObjectId()
    t3_id = ObjectId()

    enrollments = _FakeCollection(
        [{"_id": ObjectId(), "student_uid": user_uid, "subject_id": subject_id, "enrolled_at": now}]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": t1_id,
                "subject_id": subject_id,
                "title": "Due soon, high points",
                "deadline": now + timedelta(hours=4),
                "points": 10,
                "task_type": "assignment",
                "type": "individual",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": t2_id,
                "subject_id": subject_id,
                "title": "Later, low points",
                "deadline": now + timedelta(days=10),
                "points": 2,
                "task_type": "assignment",
                "type": "individual",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": t3_id,
                "subject_id": subject_id,
                "title": "Overdue, medium points",
                "deadline": now - timedelta(hours=1),
                "points": 5,
                "task_type": "assignment",
                "type": "individual",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    submissions = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "enrollments":
            return enrollments
        if name == "tasks":
            return tasks
        if name == "submissions":
            return submissions
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.ai.task_scheduler.get_collection", fake_get_collection)

    context = UserContext(
        user_uid=user_uid,
        workload_preference="balanced",
        reminder_frequency="daily",
        task_completion_pattern=TaskCompletionPattern(),
        created_at=now,
        updated_at=now,
    )
    scheduler = TaskScheduler(context_manager=_FakeContextManager(context=context, workload={"pending_count": 3}))
    schedule = await scheduler.generate_schedule(user_uid)

    ids = [row.task.id for row in schedule.tasks]
    assert ids[0] == str(t1_id)
    assert str(t1_id) in ids
    assert str(t2_id) in ids


@pytest.mark.asyncio
async def test_generate_schedule_excludes_submitted_tasks(monkeypatch):
    user_uid = "student-1"
    subject_id = ObjectId()
    now = datetime.utcnow()

    t1_id = ObjectId()
    t2_id = ObjectId()

    enrollments = _FakeCollection(
        [{"_id": ObjectId(), "student_uid": user_uid, "subject_id": subject_id, "enrolled_at": now}]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": t1_id,
                "subject_id": subject_id,
                "title": "Submitted task",
                "deadline": now + timedelta(days=1),
                "points": 10,
                "task_type": "assignment",
                "type": "individual",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": t2_id,
                "subject_id": subject_id,
                "title": "Pending task",
                "deadline": now + timedelta(days=2),
                "points": 10,
                "task_type": "assignment",
                "type": "individual",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    submissions = _FakeCollection([{"_id": ObjectId(), "task_id": t1_id, "student_uid": user_uid, "submitted_at": now}])

    def fake_get_collection(name: str):
        if name == "enrollments":
            return enrollments
        if name == "tasks":
            return tasks
        if name == "submissions":
            return submissions
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.ai.task_scheduler.get_collection", fake_get_collection)

    context = UserContext(
        user_uid=user_uid,
        workload_preference="balanced",
        reminder_frequency="daily",
        task_completion_pattern=TaskCompletionPattern(),
        created_at=now,
        updated_at=now,
    )
    scheduler = TaskScheduler(context_manager=_FakeContextManager(context=context, workload={"pending_count": 1}))
    schedule = await scheduler.generate_schedule(user_uid)

    ids = [row.task.id for row in schedule.tasks]
    assert str(t1_id) not in ids
    assert str(t2_id) in ids
