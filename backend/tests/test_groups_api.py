from __future__ import annotations

from datetime import datetime

import pytest
from bson import ObjectId
from fastapi import FastAPI
import httpx

from app.api import groups as groups_api
from app.utils import dependencies


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, *, length=None):
        return list(self._docs)


class _InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def _match(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in v["$in"]:
                    return False
                continue
            if isinstance(v, dict) and "$exists" in v:
                exists = k in doc
                if bool(v["$exists"]) != exists:
                    return False
                continue
            if doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: dict, sort=None):
        for d in self._docs:
            if self._match(d, query):
                return d
        return None

    def find(self, query: dict):
        return _FakeCursor([d for d in self._docs if self._match(d, query)])

    async def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self._docs.append(doc)
        return _InsertOneResult(doc["_id"])

    async def insert_many(self, docs: list[dict]):
        for d in docs:
            if "_id" not in d:
                d["_id"] = ObjectId()
            self._docs.append(d)

    async def delete_many(self, query: dict):
        self._docs = [d for d in self._docs if not self._match(d, query)]

    async def delete_one(self, query: dict):
        for i, d in enumerate(self._docs):
            if self._match(d, query):
                self._docs.pop(i)
                return


@pytest.mark.asyncio
async def test_groups_create_denies_student(monkeypatch):
    app = FastAPI()
    app.include_router(groups_api.router, prefix="/api/groups")

    async def override_current_user():
        return {"uid": "s1", "role": "student"}

    app.dependency_overrides[dependencies.get_current_user] = override_current_user

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/groups", json={"task_id": str(ObjectId()), "regenerate": False})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_groups_create_and_list_teacher(monkeypatch):
    teacher_uid = "t1"
    subject_oid = ObjectId()
    task_oid = ObjectId()
    now = datetime.utcnow()

    tasks = _FakeCollection(
        [
            {
                "_id": task_oid,
                "subject_id": subject_oid,
                "type": "group",
                "group_settings": {"group_size": 2, "shuffle": True},
                "problem_statements": ["P1", "P2"],
                "created_at": now,
                "updated_at": now,
            }
        ]
    )
    subjects = _FakeCollection([{"_id": subject_oid, "teacher_uid": teacher_uid}])
    enrollments = _FakeCollection(
        [
            {"_id": ObjectId(), "subject_id": subject_oid, "student_uid": "s1", "enrolled_at": now},
            {"_id": ObjectId(), "subject_id": subject_oid, "student_uid": "s2", "enrolled_at": now},
            {"_id": ObjectId(), "subject_id": subject_oid, "student_uid": "s3", "enrolled_at": now},
        ]
    )
    group_sets = _FakeCollection([])
    groups = _FakeCollection([])
    submissions = _FakeCollection([])

    def fake_get_collection(name: str):
        if name == "tasks":
            return tasks
        if name == "subjects":
            return subjects
        if name == "enrollments":
            return enrollments
        if name == "group_sets":
            return group_sets
        if name == "groups":
            return groups
        if name == "submissions":
            return submissions
        raise AssertionError(f"Unexpected collection: {name}")

    monkeypatch.setattr("app.services.group_service.get_collection", fake_get_collection)
    monkeypatch.setattr("app.api.groups.get_collection", fake_get_collection)

    app = FastAPI()
    app.include_router(groups_api.router, prefix="/api/groups")

    async def override_current_user():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_user] = override_current_user

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post("/api/groups", json={"task_id": str(task_oid), "regenerate": False})
        assert create.status_code == 201
        body = create.json()
        assert body["task_id"] == str(task_oid)
        assert body["group_set_id"]
        assert len(body["groups"]) >= 1

        create_again = await client.post("/api/groups", json={"task_id": str(task_oid), "regenerate": False})
        assert create_again.status_code == 409

        listed = await client.get("/api/groups", params={"task_id": str(task_oid)})
        assert listed.status_code == 200
        listed_body = listed.json()
        assert listed_body["group_set_id"] == body["group_set_id"]
        assert len(listed_body["groups"]) == len(body["groups"])
