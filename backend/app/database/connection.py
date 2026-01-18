from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db_name]


async def connect_to_mongo() -> None:
    global _client
    if _client is not None:
        return

    _client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        uuidRepresentation="standard",
    )


async def close_mongo_connection() -> None:
    global _client
    if _client is None:
        return

    _client.close()
    _client = None


async def ensure_mongo_indexes() -> None:
    users_collection = get_db()["users"]
    subjects_collection = get_db()["subjects"]
    enrollments_collection = get_db()["enrollments"]
    tasks_collection = get_db()["tasks"]
    submissions_collection = get_db()["submissions"]
    user_context_collection = get_db()["user_context"]

    pipeline = [
        {"$match": {"uid": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$uid", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]

    async for dup in users_collection.aggregate(pipeline):
        uid = dup.get("_id")
        if not uid:
            continue

        docs = await (
            users_collection.find({"uid": uid})
            .sort([("updated_at", -1), ("_id", -1)])
            .to_list(length=None)
        )

        if len(docs) <= 1:
            continue

        delete_ids = [doc["_id"] for doc in docs[1:]]
        await users_collection.delete_many({"_id": {"$in": delete_ids}})

    await users_collection.create_index([("uid", ASCENDING)], unique=True, name="uniq_users_uid")
    await subjects_collection.create_index(
        [("join_code", ASCENDING)], unique=True, name="uniq_subjects_join_code"
    )
    await subjects_collection.create_index(
        [("teacher_uid", ASCENDING), ("updated_at", ASCENDING)],
        name="idx_subjects_teacher_uid_updated_at",
    )
    await enrollments_collection.create_index(
        [("subject_id", ASCENDING), ("student_uid", ASCENDING)],
        unique=True,
        name="uniq_enrollments_subject_student",
    )
    await enrollments_collection.create_index(
        [("student_uid", ASCENDING), ("updated_at", ASCENDING)],
        name="idx_enrollments_student_uid_updated_at",
    )
    await enrollments_collection.create_index(
        [("subject_id", ASCENDING), ("enrolled_at", ASCENDING)],
        name="idx_enrollments_subject_enrolled_at",
    )
    await tasks_collection.create_index(
        [("subject_id", ASCENDING), ("deadline", ASCENDING)],
        name="idx_tasks_subject_deadline",
    )
    await tasks_collection.create_index(
        [("subject_id", ASCENDING), ("updated_at", ASCENDING)],
        name="idx_tasks_subject_updated_at",
    )
    await submissions_collection.create_index(
        [("task_id", ASCENDING), ("student_uid", ASCENDING)],
        unique=True,
        name="uniq_submissions_task_student",
    )
    await submissions_collection.create_index(
        [("task_id", ASCENDING), ("submitted_at", ASCENDING)],
        name="idx_submissions_task_submitted_at",
    )
    await submissions_collection.create_index(
        [("student_uid", ASCENDING), ("submitted_at", ASCENDING)],
        name="idx_submissions_student_submitted_at",
    )
    await user_context_collection.create_index(
        [("user_uid", ASCENDING)],
        unique=True,
        name="uniq_user_context_user_uid",
    )
