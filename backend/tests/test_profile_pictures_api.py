from __future__ import annotations

import asyncio
from datetime import datetime
from io import BytesIO

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI

from app.api import auth as auth_api
from app.api import profile_pictures as profile_pictures_api
from app.utils import dependencies


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    async def find_one(self, query: dict, sort=None):
        for d in self._docs:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(d)
        return None

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        found_idx = None
        for i, d in enumerate(self._docs):
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                found_idx = i
                break

        if found_idx is None:
            if not upsert:
                return
            base = dict(query)
            self._docs.append(base)
            found_idx = len(self._docs) - 1

        doc = self._docs[found_idx]
        set_doc = update.get("$set") if isinstance(update, dict) else None
        if isinstance(set_doc, dict):
            doc.update(set_doc)

    async def delete_one(self, query: dict):
        for i, d in enumerate(list(self._docs)):
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                self._docs.pop(i)
                return


class _FakeBucket:
    def __init__(self):
        self.files: dict[ObjectId, dict] = {}
        self.chunks: dict[ObjectId, bytes] = {}
        self._lock = asyncio.Lock()

    async def upload_from_stream(self, filename: str, source: bytes, metadata: dict, content_type: str):
        async with self._lock:
            fid = ObjectId()
            self.files[fid] = {
                "_id": fid,
                "filename": filename,
                "metadata": dict(metadata or {}),
                "contentType": content_type,
                "length": len(source),
                "uploadDate": datetime.utcnow(),
            }
            self.chunks[fid] = bytes(source)
        await asyncio.sleep(0)
        return fid

    async def delete(self, file_id: ObjectId):
        async with self._lock:
            self.files.pop(file_id, None)
            self.chunks.pop(file_id, None)

    async def open_download_stream(self, file_id: ObjectId):
        if file_id not in self.chunks:
            raise FileNotFoundError
        data = self.chunks[file_id]

        class _Out:
            def __init__(self, payload: bytes):
                self._payload = payload
                self._offset = 0

            async def readchunk(self):
                if self._offset >= len(self._payload):
                    return b""
                end = min(len(self._payload), self._offset + 64 * 1024)
                chunk = self._payload[self._offset : end]
                self._offset = end
                return chunk

        return _Out(data)


@pytest.mark.asyncio
async def test_teacher_upload_and_cleanup(monkeypatch):
    teacher_uid = "t1"
    users = _FakeCollection([{"uid": teacher_uid, "role": "teacher", "email": "t@x.com", "name": "T", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}])
    tmeta = _FakeCollection([])
    smeta = _FakeCollection([])

    teacher_bucket = _FakeBucket()
    student_bucket = _FakeBucket()

    def fake_get_collection(name: str):
        if name == "users":
            return users
        if name == "teacher_profile_pictures":
            return tmeta
        if name == "student_profile_pictures":
            return smeta
        raise AssertionError(f"Unexpected collection: {name}")

    def fake_bucket(bucket_name: str):
        if bucket_name == "teacher_profile_pics":
            return teacher_bucket
        if bucket_name == "student_profile_pics":
            return student_bucket
        raise AssertionError(f"Unexpected bucket: {bucket_name}")

    monkeypatch.setattr("app.api.auth.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures._gridfs_bucket", fake_bucket)

    app = FastAPI()
    app.include_router(auth_api.router, prefix="/api/auth")
    app.include_router(profile_pictures_api.router, prefix="/api/profile-pictures")

    async def override_current_user():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_user] = override_current_user

    jpg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 20
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res1 = await client.post("/api/auth/me/photo", files={"file": ("a.jpg", jpg, "image/jpeg")})
        assert res1.status_code == 200
        user1 = res1.json()
        assert user1["photo_url"].startswith("/api/profile-pictures/public/")
        first_file_id = (await tmeta.find_one({"user_uid": teacher_uid}))["gridfs_file_id"]
        assert first_file_id in teacher_bucket.files

        res2 = await client.post("/api/auth/me/photo", files={"file": ("b.png", png, "image/png")})
        assert res2.status_code == 200
        second_file_id = (await tmeta.find_one({"user_uid": teacher_uid}))["gridfs_file_id"]
        assert second_file_id in teacher_bucket.files
        assert first_file_id not in teacher_bucket.files

        public_id = (await tmeta.find_one({"user_uid": teacher_uid}))["public_id"]
        res3 = await client.get(f"/api/profile-pictures/public/{public_id}")
        assert res3.status_code == 200
        assert res3.headers["content-type"].startswith("image/")


@pytest.mark.asyncio
async def test_student_upload_unsupported_type(monkeypatch):
    student_uid = "s1"
    users = _FakeCollection([{"uid": student_uid, "role": "student", "email": "s@x.com", "name": "S", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}])
    tmeta = _FakeCollection([])
    smeta = _FakeCollection([])
    teacher_bucket = _FakeBucket()
    student_bucket = _FakeBucket()

    def fake_get_collection(name: str):
        if name == "users":
            return users
        if name == "teacher_profile_pictures":
            return tmeta
        if name == "student_profile_pictures":
            return smeta
        raise AssertionError(f"Unexpected collection: {name}")

    def fake_bucket(bucket_name: str):
        if bucket_name == "teacher_profile_pics":
            return teacher_bucket
        if bucket_name == "student_profile_pics":
            return student_bucket
        raise AssertionError(f"Unexpected bucket: {bucket_name}")

    monkeypatch.setattr("app.api.auth.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures._gridfs_bucket", fake_bucket)

    app = FastAPI()
    app.include_router(auth_api.router, prefix="/api/auth")

    async def override_current_user():
        return {"uid": student_uid, "role": "student"}

    app.dependency_overrides[dependencies.get_current_user] = override_current_user

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/auth/me/photo", files={"file": ("a.gif", b"GIF89a", "image/gif")})
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_concurrent_upload_superseded(monkeypatch):
    teacher_uid = "t2"
    users = _FakeCollection([{"uid": teacher_uid, "role": "teacher", "email": "t2@x.com", "name": "T2", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}])
    tmeta = _FakeCollection([])
    smeta = _FakeCollection([])
    teacher_bucket = _FakeBucket()
    student_bucket = _FakeBucket()

    def fake_get_collection(name: str):
        if name == "users":
            return users
        if name == "teacher_profile_pictures":
            return tmeta
        if name == "student_profile_pictures":
            return smeta
        raise AssertionError(f"Unexpected collection: {name}")

    def fake_bucket(bucket_name: str):
        if bucket_name == "teacher_profile_pics":
            return teacher_bucket
        if bucket_name == "student_profile_pics":
            return student_bucket
        raise AssertionError(f"Unexpected bucket: {bucket_name}")

    monkeypatch.setattr("app.api.auth.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures.get_collection", fake_get_collection)
    monkeypatch.setattr("app.services.profile_pictures._gridfs_bucket", fake_bucket)

    app = FastAPI()
    app.include_router(auth_api.router, prefix="/api/auth")

    async def override_current_user():
        return {"uid": teacher_uid, "role": "teacher"}

    app.dependency_overrides[dependencies.get_current_user] = override_current_user

    jpg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 20

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r1, r2 = await asyncio.gather(
            client.post("/api/auth/me/photo", files={"file": ("a.jpg", jpg, "image/jpeg")}),
            client.post("/api/auth/me/photo", files={"file": ("b.jpg", jpg, "image/jpeg")}),
        )
        statuses = sorted([r1.status_code, r2.status_code])
        assert statuses in ([200, 200], [200, 409])
        meta = await tmeta.find_one({"user_uid": teacher_uid})
        assert isinstance(meta.get("gridfs_file_id"), ObjectId)
        assert meta["gridfs_file_id"] in teacher_bucket.files
