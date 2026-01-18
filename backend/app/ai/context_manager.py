from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database.collections import get_collection
from app.models.context import TaskCompletionPattern, UserContext, UserContextUpdateRequest


class ContextManager:
    async def get_user_context(self, user_uid: str) -> UserContext:
        collection = get_collection("user_context")
        doc = await collection.find_one({"user_uid": user_uid})
        if doc:
            return self._deserialize_context(doc)

        now = datetime.utcnow()
        created = {
            "user_uid": user_uid,
            "workload_preference": "balanced",
            "reminder_frequency": "daily",
            "task_completion_pattern": TaskCompletionPattern().model_dump(),
            "created_at": now,
            "updated_at": now,
        }

        await collection.update_one(
            {"user_uid": user_uid},
            {"$setOnInsert": created},
            upsert=True,
        )
        doc = await collection.find_one({"user_uid": user_uid})
        return self._deserialize_context(doc)

    async def update_context(self, user_uid: str, data: UserContextUpdateRequest) -> UserContext:
        update: dict[str, Any] = {"updated_at": datetime.utcnow()}
        payload = data.model_dump(exclude_unset=True)
        if "workload_preference" in payload:
            update["workload_preference"] = payload["workload_preference"]
        if "reminder_frequency" in payload:
            update["reminder_frequency"] = payload["reminder_frequency"]
        if "task_completion_pattern" in payload and payload["task_completion_pattern"] is not None:
            update["task_completion_pattern"] = payload["task_completion_pattern"]

        collection = get_collection("user_context")
        await collection.update_one({"user_uid": user_uid}, {"$set": update}, upsert=True)
        doc = await collection.find_one({"user_uid": user_uid})
        return self._deserialize_context(doc)

    async def get_workload(self, user_uid: str) -> dict[str, Any]:
        enrollments_collection = get_collection("enrollments")
        tasks_collection = get_collection("tasks")
        submissions_collection = get_collection("submissions")

        enrollments = await enrollments_collection.find({"student_uid": user_uid}).to_list(length=None)
        subject_oids = [e.get("subject_id") for e in enrollments if e.get("subject_id")]
        if not subject_oids:
            return {
                "pending_count": 0,
                "overdue_count": 0,
                "due_soon_count": 0,
                "pending_points": 0,
                "updated_at": datetime.utcnow(),
            }

        tasks = await tasks_collection.find({"subject_id": {"$in": subject_oids}}).to_list(length=None)
        submissions = await submissions_collection.find({"student_uid": user_uid}).to_list(length=None)
        submitted_task_ids = {s.get("task_id") for s in submissions if s.get("task_id")}

        now = datetime.utcnow()
        pending_count = 0
        overdue_count = 0
        due_soon_count = 0
        pending_points = 0

        for t in tasks:
            task_id = t.get("_id")
            if not task_id:
                continue
            if task_id in submitted_task_ids:
                continue

            task_type = str(t.get("task_type") or "").lower()
            if "reading" in task_type or "resource" in task_type:
                continue

            pending_count += 1
            points = t.get("points")
            if isinstance(points, int):
                pending_points += max(0, points)

            deadline = t.get("deadline")
            if deadline:
                if deadline < now:
                    overdue_count += 1
                elif (deadline - now).total_seconds() <= 3 * 24 * 3600:
                    due_soon_count += 1

        return {
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count,
            "pending_points": pending_points,
            "updated_at": now,
        }

    def _deserialize_context(self, doc: dict) -> UserContext:
        raw_pattern = doc.get("task_completion_pattern") or {}
        pattern = (
            raw_pattern if isinstance(raw_pattern, dict) else TaskCompletionPattern().model_dump()
        )
        created_at = doc.get("created_at") or datetime.utcnow()
        updated_at = doc.get("updated_at") or created_at
        return UserContext(
            user_uid=doc.get("user_uid") or "",
            workload_preference=doc.get("workload_preference") or "balanced",
            reminder_frequency=doc.get("reminder_frequency") or "daily",
            task_completion_pattern=TaskCompletionPattern(**pattern),
            created_at=created_at,
            updated_at=updated_at,
        )
