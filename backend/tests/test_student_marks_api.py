from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI

from app.api import submissions as submissions_api
from app.utils import dependencies


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, _spec):
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def find(self, query: dict):
        return _FakeCursor([d for d in self._docs if self._match(d, query)])

    async def find_one(self, query: dict, sort=None):
        matches = [d for d in self._docs if self._match(d, query)]
        if not matches:
            return None
        return matches[0]

    def _match(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in set(v["$in"]):
                    return False
                continue

            if k == "member_uids":
                if v not in (doc.get("member_uids") or []):
                    return False
                continue

            if doc.get(k) != v:
                return False
        return True


@pytest.mark.asyncio
async def test_list_student_marks_includes_group_and_individual_submissions(monkeypatch):
    teacher_uid = "t1"
    student_uid = "s1"
    subject_oid = ObjectId()
    now = datetime.utcnow()

    quiz_task_oid = ObjectId()
    assignment_task_oid = ObjectId()
    project_task_oid = ObjectId()
    extra_task_oid = ObjectId()

    tasks = _FakeCollection(
        [
            {
                "_id": quiz_task_oid,
                "subject_id": subject_oid,
                "title": "Quiz 1",
                "task_type": "Quiz",
                "points": 10,
                "type": "individual",
                "deadline": now + timedelta(days=1),
                "updated_at": now,
                "created_at": now,
            },
            {
                "_id": assignment_task_oid,
                "subject_id": subject_oid,
                "title": "Assignment 1",
                "task_type": "Assignment",
                "points": 20,
                "type": "individual",
                "deadline": now + timedelta(days=2),
                "updated_at": now,
                "created_at": now,
            },
            {
                "_id": project_task_oid,
                "subject_id": subject_oid,
                "title": "Project 1",
                "task_type": "Project",
                "points": 30,
                "type": "group",
                "deadline": now + timedelta(days=3),
                "updated_at": now,
                "created_at": now,
            },
            {
                "_id": extra_task_oid,
                "subject_id": subject_oid,
                "title": "Extra Credit 1",
                "task_type": "Extra Credit",
                "points": 5,
                "type": "individual",
                "deadline": None,
                "updated_at": now,
                "created_at": now,
            },
        ]
    )

    subjects = _FakeCollection([{"_id": subject_oid, "teacher_uid": teacher_uid}])

    group_oid = ObjectId()
    groups = _FakeCollection([{"_id": group_oid, "task_id": project_task_oid, "member_uids": [student_uid]}])

    submissions = _FakeCollection(
        [
            {
                "_id": ObjectId(),
                "task_id": quiz_task_oid,
                "subject_id": subject_oid,
                "student_uid": student_uid,
                "group_id": None,
                "content": "c",
                "submitted_at": now,
                "created_at": now,
                "updated_at": now,
                "score": 9.0,
                "evaluation": {"status": "completed", "ai_score": 95},
            },
            {
                "_id": ObjectId(),
                "task_id": assignment_task_oid,
                "subject_id": subject_oid,
                "student_uid": student_uid,
                "group_id": None,
                "content": "c2",
                "submitted_at": now,
                "created_at": now,
                "updated_at": now,
                "score": None,
                "evaluation": {"status": "pending"},
            },
            {
                "_id": ObjectId(),
                "task_id": project_task_oid,
                "subject_id": subject_oid,
                "student_uid": "leader",
                "group_id": group_oid,
                "content": "gc",
                "submitted_at": now,
                "created_at": now,
                "updated_at": now,
                "score": 25.0,
                "evaluation": {"status": "completed"},
            },
        ]
    )

    def fake_get_collection(name: str):
        if name == "subjects":
            return subjects
        if name == "tasks":
            return tasks
        if name == "groups":
            return groups
        if name == "submissions":
            return submissions
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.api.submissions.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(submissions_api.router, prefix="/api/submissions")

    async def override_current_teacher():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_teacher] = override_current_teacher

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            "/api/submissions/student-marks",
            params={"subject_id": str(subject_oid), "student_uid": student_uid},
        )
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 4

        by_task = {row["task_id"]: row for row in body}
        assert by_task[str(quiz_task_oid)]["score"] == 9.0
        assert by_task[str(quiz_task_oid)]["status"] == "completed"
        assert by_task[str(quiz_task_oid)]["ai_score"] == 95

        assert by_task[str(assignment_task_oid)]["score"] is None
        assert by_task[str(assignment_task_oid)]["status"] == "pending"

        assert by_task[str(project_task_oid)]["score"] == 25.0
        assert by_task[str(project_task_oid)]["group_id"] == str(group_oid)

        assert by_task[str(extra_task_oid)]["submission_id"] is None
