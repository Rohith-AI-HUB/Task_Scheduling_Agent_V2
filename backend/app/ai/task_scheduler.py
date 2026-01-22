from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from app.ai.context_manager import ContextManager
from app.database.collections import get_collection
from app.models.context import AIScheduleResponse, PriorityBand, ScheduledTask, UserContext
from app.models.task import TaskResponse

logger = logging.getLogger(__name__)


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
        submitted_task_ids: set[Any] = set()

        individual_submissions = await submissions_collection.find(
            {"student_uid": user_uid, "group_id": None}
        ).to_list(length=None)
        submitted_task_ids.update({s.get("task_id") for s in individual_submissions if s.get("task_id")})

        group_task_ids = [t["_id"] for t in tasks if t.get("type") == "group" and t.get("_id")]
        if group_task_ids:
            groups_collection = get_collection("groups")
            groups = await groups_collection.find(
                {"task_id": {"$in": group_task_ids}, "member_uids": user_uid}
            ).to_list(length=None)
            group_ids = [g.get("_id") for g in groups if g.get("_id")]
            if group_ids:
                group_submissions = await submissions_collection.find(
                    {"group_id": {"$in": group_ids}}
                ).to_list(length=None)
                submitted_task_ids.update(
                    {s.get("task_id") for s in group_submissions if s.get("task_id")}
                )

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

    async def generate_schedule_with_explanations(
        self, user_uid: str, include_explanations: bool = True
    ) -> AIScheduleResponse:
        """
        Generate schedule with optional Groq-powered explanations.

        Args:
            user_uid: Student's user ID
            include_explanations: Whether to add AI explanations

        Returns:
            AIScheduleResponse with optional explanations per task
        """
        # First generate the base schedule
        schedule = await self.generate_schedule(user_uid)

        if not include_explanations or not schedule.tasks:
            return schedule

        # Try to add Groq explanations
        try:
            from app.services.groq_service import groq_service

            if not groq_service.is_available():
                logger.debug("Groq not available, returning schedule without explanations")
                return schedule

            # Get context for explanations
            context = await self._context_manager.get_user_context(user_uid)
            workload = await self._context_manager.get_workload(user_uid)

            # Prepare task data for Groq
            tasks_for_groq = []
            now = datetime.utcnow()

            # Get subject names for context
            subjects_collection = get_collection("subjects")
            subject_ids = list(set(t.task.subject_id for t in schedule.tasks[:10]))
            subjects = await subjects_collection.find(
                {"_id": {"$in": [self._to_object_id(sid) for sid in subject_ids]}}
            ).to_list(length=None)
            subject_names = {str(s["_id"]): s.get("name", "Unknown") for s in subjects}

            for scheduled_task in schedule.tasks[:10]:  # Limit to 10 for API efficiency
                task = scheduled_task.task
                deadline = task.deadline

                if deadline:
                    days_remaining = (deadline - now).total_seconds() / 86400
                    deadline_str = deadline.strftime("%Y-%m-%d %H:%M")
                else:
                    days_remaining = None
                    deadline_str = "No deadline"

                tasks_for_groq.append({
                    "title": task.title,
                    "subject": subject_names.get(task.subject_id, "Unknown"),
                    "deadline": deadline_str,
                    "days_remaining": round(days_remaining, 1) if days_remaining is not None else None,
                    "points": task.points or 0,
                    "priority_score": scheduled_task.priority,
                    "band": scheduled_task.band
                })

            # Get explanations from Groq
            explanations = await groq_service.explain_schedule(
                user_uid=user_uid,
                workload_preference=context.workload_preference,
                pending_tasks=workload.get("pending_count", 0),
                overdue_tasks=workload.get("overdue_count", 0),
                tasks=tasks_for_groq
            )

            # Add explanations to scheduled tasks
            for i, scheduled_task in enumerate(schedule.tasks[:len(explanations)]):
                if i < len(explanations):
                    scheduled_task.explanation = explanations[i]

            return schedule

        except Exception as e:
            logger.warning(f"Failed to generate schedule explanations: {e}")
            return schedule

    def _to_object_id(self, id_str: str):
        """Convert string ID to ObjectId if needed"""
        try:
            from bson import ObjectId
            return ObjectId(id_str) if not isinstance(id_str, ObjectId) else id_str
        except Exception:
            return id_str


def preprocess_schedule_for_groq(
    context: UserContext,
    workload: dict[str, Any],
    scheduled_tasks: List[ScheduledTask],
    subject_names: dict[str, str]
) -> dict[str, Any]:
    """
    Preprocess schedule data for Groq explanations.

    Args:
        context: User's context/preferences
        workload: Workload metrics
        scheduled_tasks: List of prioritized tasks
        subject_names: Mapping of subject_id to subject name

    Returns:
        Preprocessed data dict ready for Groq
    """
    now = datetime.utcnow()

    tasks_data = []
    for scheduled_task in scheduled_tasks[:10]:  # Limit to 10
        task = scheduled_task.task
        deadline = task.deadline

        if deadline:
            days_remaining = (deadline - now).total_seconds() / 86400
            deadline_str = deadline.strftime("%Y-%m-%d")
        else:
            days_remaining = None
            deadline_str = "No deadline"

        tasks_data.append({
            "title": task.title,
            "subject": subject_names.get(task.subject_id, "Unknown"),
            "deadline": deadline_str,
            "days_remaining": round(days_remaining, 1) if days_remaining is not None else None,
            "points": task.points or 0,
            "priority_score": scheduled_task.priority,
            "band": scheduled_task.band
        })

    return {
        "student_context": {
            "workload_preference": context.workload_preference,
            "pending_tasks": workload.get("pending_count", 0),
            "overdue_tasks": workload.get("overdue_count", 0)
        },
        "top_tasks": tasks_data
    }
