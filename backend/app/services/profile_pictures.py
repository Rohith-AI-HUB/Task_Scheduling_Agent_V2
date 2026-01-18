from __future__ import annotations

from datetime import datetime
import logging
import secrets
from pathlib import Path
from typing import Any, AsyncIterator

from bson import ObjectId
from fastapi import HTTPException, status, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.config import settings
from app.database.connection import get_db
from app.database.collections import get_collection

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _bucket_and_collection_for_role(role: str) -> tuple[str, str]:
    if role == "teacher":
        return "teacher_profile_pics", "teacher_profile_pictures"
    return "student_profile_pics", "student_profile_pictures"


def _validate_image_bytes(content_type: str, data: bytes) -> None:
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    max_bytes = int(settings.max_upload_bytes)
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    if content_type == "image/jpeg":
        if not (len(data) >= 3 and data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JPEG file")
    elif content_type == "image/png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PNG file")
    elif content_type == "image/webp":
        if not (len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid WEBP file")


def _gridfs_bucket(bucket_name: str) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name=bucket_name)


async def _read_upload_file(file: UploadFile) -> tuple[bytes, str, str]:
    content_type = str(file.content_type or "").lower().strip()
    data = bytearray()
    max_bytes = int(settings.max_upload_bytes)
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    return bytes(data), content_type, str(file.filename or "profile")


def _new_public_id() -> str:
    return secrets.token_urlsafe(18)


def _delete_legacy_avatar(photo_url: Any) -> None:
    if not isinstance(photo_url, str) or not photo_url.startswith("/uploads/avatars/"):
        return
    filename = photo_url.split("/uploads/avatars/", 1)[1]
    try:
        p = Path(settings.uploads_dir) / "avatars" / filename
        if p.exists() and p.is_file():
            p.unlink()
    except Exception:
        logger.warning("profile_picture.legacy_delete_failed", exc_info=True)


async def upsert_profile_picture(current_user: dict, file: UploadFile) -> str:
    role = str(current_user.get("role") or "").strip().lower()
    uid = str(current_user.get("uid") or "").strip()
    if not uid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user")

    bucket_name, meta_collection_name = _bucket_and_collection_for_role(role)
    meta_collection = get_collection(meta_collection_name)
    users_collection = get_collection("users")

    logger.info("profile_picture.upload.start uid=%s role=%s", uid, role)

    data, content_type, original_name = await _read_upload_file(file)
    _validate_image_bytes(content_type, data)

    uploaded_at = datetime.utcnow()
    public_id = _new_public_id()
    bucket = _gridfs_bucket(bucket_name)

    old = await meta_collection.find_one({"user_uid": uid})
    old_file_id = old.get("gridfs_file_id") if isinstance(old, dict) else None
    old_public_id = old.get("public_id") if isinstance(old, dict) else None

    new_file_id: ObjectId | None = None
    updated_user = False
    updated_meta = False

    try:
        _delete_legacy_avatar(current_user.get("photo_url"))

        new_file_id = await bucket.upload_from_stream(
            filename=f"{uid}/{original_name}",
            source=data,
            metadata={
                "user_uid": uid,
                "role": role,
                "uploaded_at": uploaded_at,
                "content_type": content_type,
                "public_id": public_id,
            },
            content_type=content_type,
        )

        await meta_collection.update_one(
            {"user_uid": uid},
            {
                "$set": {
                    "user_uid": uid,
                    "role": role,
                    "bucket": bucket_name,
                    "gridfs_file_id": new_file_id,
                    "content_type": content_type,
                    "uploaded_at": uploaded_at,
                    "public_id": public_id,
                    "length": len(data),
                }
            },
            upsert=True,
        )
        updated_meta = True

        photo_url = f"/api/profile-pictures/public/{public_id}"
        await users_collection.update_one(
            {"uid": uid},
            {
                "$set": {
                    "photo_url": photo_url,
                    "photo_public_id": public_id,
                    "photo_updated_at": uploaded_at,
                    "updated_at": uploaded_at,
                }
            },
        )
        updated_user = True

        current_meta = await meta_collection.find_one({"user_uid": uid})
        current_file_id = current_meta.get("gridfs_file_id") if isinstance(current_meta, dict) else None
        if current_file_id != new_file_id:
            logger.info("profile_picture.upload.superseded uid=%s role=%s", uid, role)
            await bucket.delete(new_file_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload superseded by another request")

        if isinstance(old_file_id, ObjectId) and old_file_id != new_file_id:
            try:
                await bucket.delete(old_file_id)
                logger.info("profile_picture.upload.old_deleted uid=%s role=%s old_public_id=%s", uid, role, old_public_id)
            except Exception:
                logger.warning("profile_picture.upload.old_delete_failed uid=%s role=%s", uid, role, exc_info=True)

        logger.info("profile_picture.upload.success uid=%s role=%s public_id=%s", uid, role, public_id)
        return photo_url
    except HTTPException:
        raise
    except Exception as e:
        logger.error("profile_picture.upload.failed uid=%s role=%s err=%s", uid, role, str(e), exc_info=True)
        if new_file_id is not None:
            try:
                await bucket.delete(new_file_id)
            except Exception:
                logger.warning("profile_picture.rollback.delete_new_failed uid=%s role=%s", uid, role, exc_info=True)

        if updated_user:
            try:
                if isinstance(old_public_id, str) and old_public_id:
                    await users_collection.update_one(
                        {"uid": uid},
                        {
                            "$set": {
                                "photo_url": f"/api/profile-pictures/public/{old_public_id}",
                                "photo_public_id": old_public_id,
                                "photo_updated_at": old.get("uploaded_at") if isinstance(old, dict) else None,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                else:
                    await users_collection.update_one(
                        {"uid": uid},
                        {"$set": {"photo_url": None, "photo_public_id": None, "photo_updated_at": None, "updated_at": datetime.utcnow()}},
                    )
            except Exception:
                logger.warning("profile_picture.rollback.restore_user_failed uid=%s role=%s", uid, role, exc_info=True)

        if updated_meta:
            try:
                if isinstance(old, dict) and old:
                    await meta_collection.update_one({"user_uid": uid}, {"$set": old}, upsert=True)
                else:
                    await meta_collection.delete_one({"user_uid": uid})
            except Exception:
                logger.warning("profile_picture.rollback.restore_meta_failed uid=%s role=%s", uid, role, exc_info=True)

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload photo") from e


async def delete_profile_picture(current_user: dict) -> None:
    role = str(current_user.get("role") or "").strip().lower()
    uid = str(current_user.get("uid") or "").strip()
    if not uid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user")

    bucket_name, meta_collection_name = _bucket_and_collection_for_role(role)
    meta_collection = get_collection(meta_collection_name)
    users_collection = get_collection("users")
    bucket = _gridfs_bucket(bucket_name)

    logger.info("profile_picture.delete.start uid=%s role=%s", uid, role)

    meta = await meta_collection.find_one({"user_uid": uid})
    file_id = meta.get("gridfs_file_id") if isinstance(meta, dict) else None

    if isinstance(file_id, ObjectId):
        try:
            await bucket.delete(file_id)
        except Exception:
            logger.warning("profile_picture.delete.file_failed uid=%s role=%s", uid, role, exc_info=True)

    await meta_collection.delete_one({"user_uid": uid})
    await users_collection.update_one(
        {"uid": uid},
        {"$set": {"photo_url": None, "photo_public_id": None, "photo_updated_at": None, "updated_at": datetime.utcnow()}},
    )
    _delete_legacy_avatar(current_user.get("photo_url"))
    logger.info("profile_picture.delete.success uid=%s role=%s", uid, role)


async def iter_public_picture(public_id: str) -> tuple[str, AsyncIterator[bytes]]:
    value = str(public_id or "").strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    teacher_meta = get_collection("teacher_profile_pictures")
    student_meta = get_collection("student_profile_pictures")

    meta = await teacher_meta.find_one({"public_id": value})
    if not meta:
        meta = await student_meta.find_one({"public_id": value})
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    bucket_name = str(meta.get("bucket") or "")
    file_id = meta.get("gridfs_file_id")
    content_type = str(meta.get("content_type") or "application/octet-stream")
    if not bucket_name or not isinstance(file_id, ObjectId):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    bucket = _gridfs_bucket(bucket_name)
    try:
        grid_out = await bucket.open_download_stream(file_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    async def gen() -> AsyncIterator[bytes]:
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield bytes(chunk)

    return content_type, gen()
