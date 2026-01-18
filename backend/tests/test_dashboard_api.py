from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI

from app.api import dashboard as dashboard_api
from app.utils import dependencies


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, _):
        self._docs.sort(key=lambda d: d.get("deadline") or datetime.max)
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return list(self._docs)[:length]


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def find(self, query: dict):
        def matches(doc: dict) -> bool:
            for k, v in query.items():
                if isinstance(v, dict):
                    if "$in" in v and doc.get(k) not in set(v["$in"]):
                        return False
                    if "$ne" in v and doc.get(k) == v["$ne"]:
                        return False
                    if "$gte" in v and (doc.get(k) is None or doc.get(k) < v["$gte"]):
                        return False
                    if "$lte" in v and (doc.get(k) is None or doc.get(k) > v["$lte"]):
                        return False
                    continue
                if doc.get(k) != v:
                    return False
            return True

        return _FakeCursor([d for d in self._docs if matches(d)])

    async def find_one(self, query: dict, sort=None):
        for d in self._docs:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                return d
        return None


@pytest.mark.asyncio
async def test_due_soon_excludes_submitted_tasks(monkeypatch):
    now = datetime.utcnow()
    student_uid = "s1"
    subject_id = ObjectId()

    t1 = ObjectId()
    t2 = ObjectId()

    enrollments = _FakeCollection(
        [{"_id": ObjectId(), "student_uid": student_uid, "subject_id": subject_id, "enrolled_at": now}]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": t1,
                "subject_id": subject_id,
                "title": "Submitted",
                "deadline": now + timedelta(days=1),
                "updated_at": now,
            },
            {
                "_id": t2,
                "subject_id": subject_id,
                "title": "Pending",
                "deadline": now + timedelta(days=2),
                "updated_at": now,
            },
        ]
    )
    submissions = _FakeCollection(
        [
            {
                "_id": ObjectId(),
                "task_id": t1,
                "student_uid": student_uid,
                "group_id": None,
                "submitted_at": now,
            }
        ]
    )
    groups = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "enrollments":
            return enrollments
        if name == "tasks":
            return tasks
        if name == "submissions":
            return submissions
        if name == "groups":
            return groups
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.api.dashboard.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(dashboard_api.router, prefix="/api/dashboard")

    async def override_current_student():
        return {"uid": student_uid, "role": "student"}

    app.dependency_overrides[dependencies.get_current_student] = override_current_student

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/dashboard/due-soon")
        assert res.status_code == 200
        body = res.json()
        ids = [row["task_id"] for row in body["items"]]
        assert str(t1) not in ids
        assert str(t2) in ids


@pytest.mark.asyncio
async def test_upcoming_excludes_overdue_and_submitted_tasks(monkeypatch):
    now = datetime.utcnow()
    student_uid = "s1"
    subject_id = ObjectId()

    overdue = ObjectId()
    submitted = ObjectId()
    upcoming = ObjectId()

    enrollments = _FakeCollection(
        [{"_id": ObjectId(), "student_uid": student_uid, "subject_id": subject_id, "enrolled_at": now}]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": overdue,
                "subject_id": subject_id,
                "title": "Overdue",
                "deadline": now - timedelta(hours=2),
                "updated_at": now,
            },
            {
                "_id": submitted,
                "subject_id": subject_id,
                "title": "Submitted",
                "deadline": now + timedelta(days=3),
                "updated_at": now,
            },
            {
                "_id": upcoming,
                "subject_id": subject_id,
                "title": "Upcoming",
                "deadline": now + timedelta(days=4),
                "updated_at": now,
            },
        ]
    )
    submissions = _FakeCollection(
        [
            {
                "_id": ObjectId(),
                "task_id": submitted,
                "student_uid": student_uid,
                "group_id": None,
                "submitted_at": now,
            }
        ]
    )
    groups = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "enrollments":
            return enrollments
        if name == "tasks":
            return tasks
        if name == "submissions":
            return submissions
        if name == "groups":
            return groups
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.api.dashboard.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(dashboard_api.router, prefix="/api/dashboard")

    async def override_current_student():
        return {"uid": student_uid, "role": "student"}

    app.dependency_overrides[dependencies.get_current_student] = override_current_student

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/dashboard/upcoming")
        assert res.status_code == 200
        body = res.json()
        ids = [row["task_id"] for row in body["items"]]
        assert str(overdue) not in ids
        assert str(submitted) not in ids
        assert str(upcoming) in ids


@pytest.mark.asyncio
async def test_teacher_upcoming_includes_teacher_tasks(monkeypatch):
    now = datetime.utcnow()
    teacher_uid = "t1"
    subject_id = ObjectId()
    other_subject_id = ObjectId()

    upcoming = ObjectId()
    far = ObjectId()

    subjects = _FakeCollection(
        [
            {"_id": subject_id, "teacher_uid": teacher_uid, "name": "Math"},
            {"_id": other_subject_id, "teacher_uid": "t2", "name": "Other"},
        ]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": upcoming,
                "subject_id": subject_id,
                "title": "Quiz",
                "deadline": now + timedelta(days=2),
                "updated_at": now,
            },
            {
                "_id": far,
                "subject_id": subject_id,
                "title": "Far",
                "deadline": now + timedelta(days=40),
                "updated_at": now,
            },
        ]
    )
    enrollments = _FakeCollection([])
    submissions = _FakeCollection([])
    groups = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "subjects":
            return subjects
        if name == "tasks":
            return tasks
        if name == "enrollments":
            return enrollments
        if name == "submissions":
            return submissions
        if name == "groups":
            return groups
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.api.dashboard.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(dashboard_api.router, prefix="/api/dashboard")

    async def override_current_teacher():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_teacher] = override_current_teacher

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/dashboard/teacher/upcoming", params={"days": 14, "limit": 10})
        assert res.status_code == 200
        body = res.json()
        ids = [row["task_id"] for row in body["items"]]
        assert str(upcoming) in ids
        assert str(far) not in ids
