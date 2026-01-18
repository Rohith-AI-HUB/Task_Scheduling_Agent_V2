from __future__ import annotations

from datetime import datetime

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI

from app.api import tasks as tasks_api
from app.utils import dependencies


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def _match(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: dict, sort=None):
        for d in self._docs:
            if self._match(d, query):
                return d
        return None

    async def update_one(self, query: dict, update: dict):
        if "$set" not in update:
            return
        for d in self._docs:
            if self._match(d, query):
                for k, v in update["$set"].items():
                    d[k] = v
                return


@pytest.mark.asyncio
async def test_update_task_allows_clearing_evaluation_config(monkeypatch):
    teacher_uid = "t1"
    subject_oid = ObjectId()
    task_oid = ObjectId()
    now = datetime.utcnow()

    tasks = _FakeCollection(
        [
            {
                "_id": task_oid,
                "subject_id": subject_oid,
                "title": "T",
                "description": None,
                "deadline": None,
                "points": None,
                "task_type": None,
                "type": "individual",
                "problem_statements": [],
                "group_settings": None,
                "evaluation_config": {"code": {"language": "python", "timeout_ms": 2000, "test_cases": []}},
                "created_at": now,
                "updated_at": now,
            }
        ]
    )
    subjects = _FakeCollection([{"_id": subject_oid, "teacher_uid": teacher_uid}])
    enrollments = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "tasks":
            return tasks
        if name == "subjects":
            return subjects
        if name == "enrollments":
            return enrollments
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.api.tasks.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(tasks_api.router, prefix="/api/tasks")

    async def override_current_teacher():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_teacher] = override_current_teacher

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.put(f"/api/tasks/{task_oid}", json={"evaluation_config": None})
        assert res.status_code == 200
        body = res.json()
        assert body["evaluation_config"] is None
