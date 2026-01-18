from __future__ import annotations

from datetime import datetime
from typing import Any

from app.ai.context_manager import ContextManager
from app.database.collections import get_collection
from app.models.context import AIScheduleResponse, PriorityBand, ScheduledTask, UserContext
from app.models.task import TaskResponse


class TaskScheduler:
    def __init__(self, context_manager: ContextManager | None = None) -> None:
        self._context_manager = context_manager or ContextManager()

    async def generate_schedule(self, user_uid: str) -> AIScheduleResponse:
        context = await self._context_manager.get_user_context(user_uid)
        workload = await self._context_manager.get_workload(user_uid)

        enrollments_collection = get_collection("enrollments")
        tasks_collection = get_collection("tasks")
        submissions_collection = get_collection("submissions")

        enrollments = await enrollments_collection.find({"student_uid": user_uid}).to_list(length=None)
        subject_oids = [e.get("subject_id") for e in enrollments if e.get("subject_id")]
        if not subject_oids:
            return AIScheduleResponse(generated_at=datetime.utcnow(), tasks=[])

        tasks = await tasks_collection.find({"subject_id": {"$in": subject_oids}}).to_list(length=None)
        submissions = await submissions_collection.find({"student_uid": user_uid}).to_list(length=None)
        submitted_task_ids = {s.get("task_id") for s in submissions if s.get("task_id")}

        candidate_tasks: list[dict] = []
        for t in tasks:
            if not t.get("_id"):
                continue
            if t.get("_id") in submitted_task_ids:
                continue
            task_type = str(t.get("task_type") or "").lower()
            if "reading" in task_type or "resource" in task_type:
                continue
            candidate_tasks.append(t)

        max_points = 0
        for t in candidate_tasks:
            points = t.get("points")
            if isinstance(points, int):
                max_points = max(max_points, points)

        now = datetime.utcnow()
        scored: list[ScheduledTask] = []
        for t in candidate_tasks:
            task = self._serialize_task(t)
            priority = self.calculate_priority(task, context, workload, max_points=max_points, now=now)
            band = self._priority_band(priority)
            scored.append(ScheduledTask(task=task, priority=priority, band=band))

        far_future = datetime.max
        scored.sort(
            key=lambda x: (
                -x.priority,
                x.task.deadline is None,
                x.task.deadline or far_future,
                x.task.updated_at,
                x.task.id,
            )
        )
        return AIScheduleResponse(generated_at=now, tasks=scored)

    def calculate_priority(
        self,
        task: TaskResponse,
        context: UserContext,
        workload: dict[str, Any],
        *,
        max_points: int,
        now: datetime,
    ) -> float:
        urgency = self._urgency_score(task.deadline, now=now)
        importance = self._importance_score(task.points, max_points=max_points)
        balance = self._balance_score(context, workload)
        priority = (urgency * 0.4) + (importance * 0.4) + (balance * 0.2)
        return float(max(0.0, min(1.0, priority)))

    def _urgency_score(self, deadline: datetime | None, *, now: datetime) -> float:
        if deadline is None:
            return 0.05
        delta = deadline - now
        days_left = delta.total_seconds() / 86400
        if days_left <= 0:
            return 1.0
        if days_left <= 1:
            return 0.95
        if days_left <= 3:
            return 0.8
        if days_left <= 7:
            return 0.5
        return max(0.1, min(0.4, 1.0 / days_left))

    def _importance_score(self, points: int | None, *, max_points: int) -> float:
        if points is None:
            return 0.1
        if max_points <= 0:
            return 0.2
        return float(max(0.0, min(1.0, points / max_points)))

    def _balance_score(self, context: UserContext, workload: dict[str, Any]) -> float:
        pending_count = int(workload.get("pending_count") or 0)
        overdue_count = int(workload.get("overdue_count") or 0)
        due_soon_count = int(workload.get("due_soon_count") or 0)

        load = pending_count + (overdue_count * 2) + due_soon_count
        normalized = min(1.0, load / 12.0)

        pref = context.workload_preference
        if pref == "heavy":
            base = 0.9
        elif pref == "light":
            base = 0.5
        else:
            base = 0.7

        return float(max(0.0, min(1.0, base + (normalized * 0.1))))

    def _priority_band(self, priority: float) -> PriorityBand:
        if priority >= 0.85:
            return "urgent"
        if priority >= 0.65:
            return "high"
        if priority >= 0.4:
            return "normal"
        return "low"

    def _serialize_task(self, doc: dict) -> TaskResponse:
        return TaskResponse(
            id=str(doc["_id"]),
            subject_id=str(doc["subject_id"]),
            title=doc.get("title") or "",
            description=doc.get("description"),
            deadline=doc.get("deadline"),
            points=doc.get("points"),
            task_type=doc.get("task_type"),
            type=doc.get("type", "individual"),
            created_at=doc.get("created_at") or datetime.utcnow(),
            updated_at=doc.get("updated_at") or datetime.utcnow(),
        )
