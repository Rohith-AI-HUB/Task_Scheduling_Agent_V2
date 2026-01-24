"""
Chat Service
Handles the chat assistant functionality with intent classification,
context gathering, and Groq integration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.intent_classifier import (
    ChatIntent,
    classify_intent,
    get_required_context,
    get_greeting_response,
)
from app.services.groq_service import groq_service, RateLimitExceeded, GroqServiceError
from app.services.credit_service import CreditService
from app.database.collections import get_collection

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat assistant interactions"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.credit_service = CreditService(db)
        self._history: Dict[str, List[Dict]] = {}  # In-memory history (per session)

    async def process_message(
        self,
        user_uid: str,
        role: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.

        Args:
            user_uid: User's ID
            role: User's role (student/teacher)
            message: User's message

        Returns:
            Dict with response, intent, context_used, credits_remaining
        """
        # Classify intent
        intent, confidence = classify_intent(message)
        logger.debug(f"Classified intent: {intent} (confidence: {confidence})")

        normalized_role = str(role or "student").lower()
        credit_status = await self.credit_service.get_credits(user_uid, normalized_role)

        # Handle special intents without Groq
        if intent == ChatIntent.GREETING:
            return {
                "response": get_greeting_response(),
                "intent": intent.value,
                "context_used": [],
                "credits_remaining": credit_status["credits_remaining"],
                "timestamp": datetime.now(timezone.utc)
            }

        if credit_status["credits_remaining"] <= 0:
            return {
                "response": "Daily message limit reached. Credits reset at midnight UTC.",
                "intent": "no_credits",
                "context_used": [],
                "credits_remaining": 0,
                "error": "NO_CREDITS",
                "timestamp": datetime.now(timezone.utc),
            }

        if not groq_service.is_available():
            return {
                "response": "AI chat is not configured. Set GROQ_API_KEY on the backend and restart the server.",
                "intent": "ai_unavailable",
                "context_used": [],
                "credits_remaining": credit_status["credits_remaining"],
                "error": "GROQ_NOT_CONFIGURED",
                "timestamp": datetime.now(timezone.utc),
            }

        # Gather context based on intent
        context = await self._gather_context(user_uid, normalized_role, intent)
        context_used = list(context.keys())

        # Generate response with Groq
        history_for_llm = (self._history.get(user_uid) or [])[-10:]

        groq_succeeded = False
        try:
            response = await groq_service.chat_response(
                user_uid=user_uid,
                message=message,
                intent=intent.value,
                context=context,
                role=normalized_role,
                history=history_for_llm,
            )
            groq_succeeded = True
        except RateLimitExceeded as e:
            response = str(e)
        except GroqServiceError as e:
            logger.warning(f"Groq error for user {user_uid}: {e}")
            response = f"Groq failed: {str(e)}"
        except Exception as e:
            logger.error(f"Chat response error: {e}")
            response = self._fallback_response(intent, context, role=normalized_role)

        credits_remaining = credit_status["credits_remaining"]
        if groq_succeeded:
            credit_result = await self.credit_service.use_credit(user_uid, normalized_role)
            if not credit_result["success"]:
                logger.warning(f"Credit update failed for user {user_uid}: {credit_result.get('error')}")
            credits_remaining = credit_result.get("credits_remaining", credits_remaining)

        # Store in history
        self._add_to_history(user_uid, "user", message, intent.value)
        self._add_to_history(user_uid, "assistant", response)

        return {
            "response": response,
            "intent": intent.value,
            "context_used": context_used,
            "credits_remaining": credits_remaining,
            "timestamp": datetime.now(timezone.utc)
        }

    async def _gather_context(
        self,
        user_uid: str,
        role: str,
        intent: ChatIntent
    ) -> Dict[str, Any]:
        """
        Gather relevant context based on intent.

        Args:
            user_uid: User's ID
            intent: Classified intent

        Returns:
            Dict with context data
        """
        context = {}
        required_context = get_required_context(intent)

        try:
            if "tasks" in required_context or "upcoming_deadlines" in required_context:
                if role == "teacher":
                    context["tasks"] = await self._get_teacher_tasks(user_uid)
                else:
                    context["tasks"] = await self._get_student_tasks(user_uid)

            if "submissions" in required_context or "pending_evaluations" in required_context:
                if role == "teacher":
                    context["submissions"] = await self._get_teacher_recent_submissions(user_uid)
                else:
                    context["submissions"] = await self._get_student_recent_submissions(user_uid)

            if "schedule" in required_context:
                if role == "teacher":
                    context["schedule"] = await self._get_teacher_overview_schedule(user_uid)
                else:
                    context["schedule"] = await self._get_schedule(user_uid)

            if "workload" in required_context:
                if role == "teacher":
                    context["workload"] = await self._get_teacher_workload(user_uid)
                else:
                    context["workload"] = await self._get_workload(user_uid)

        except Exception as e:
            logger.error(f"Error gathering context: {e}")

        return context

    async def _get_student_tasks(self, user_uid: str, limit: int = 10) -> List[Dict]:
        """Get student's upcoming tasks"""
        enrollments_collection = get_collection("enrollments")
        tasks_collection = get_collection("tasks")
        subjects_collection = get_collection("subjects")

        # Get enrolled subjects
        enrollments = await enrollments_collection.find(
            {"student_uid": user_uid}
        ).to_list(length=None)

        subject_ids = [e.get("subject_id") for e in enrollments if e.get("subject_id")]

        if not subject_ids:
            return []

        # Get subject names
        subjects = await subjects_collection.find(
            {"_id": {"$in": subject_ids}}
        ).to_list(length=None)
        subject_names = {str(s["_id"]): s.get("name", "Unknown") for s in subjects}

        # Get tasks
        now = datetime.utcnow()
        tasks = await tasks_collection.find({
            "subject_id": {"$in": subject_ids},
            "$or": [
                {"deadline": {"$gte": now}},
                {"deadline": None}
            ]
        }).sort("deadline", 1).limit(limit).to_list(length=limit)

        result = []
        for task in tasks:
            deadline = task.get("deadline")
            result.append({
                "task_id": str(task.get("_id")) if task.get("_id") else None,
                "title": task.get("title", "Untitled"),
                "subject": subject_names.get(str(task.get("subject_id")), "Unknown"),
                "deadline": deadline.strftime("%Y-%m-%d %H:%M") if deadline else "No deadline",
                "points": task.get("points", 0),
                "type": task.get("task_type", "general")
            })

        return result

    async def _get_teacher_tasks(self, teacher_uid: str, limit: int = 10) -> List[Dict]:
        """Get teacher's tasks across their classrooms"""
        subjects_collection = get_collection("subjects")
        tasks_collection = get_collection("tasks")

        subjects = await subjects_collection.find({"teacher_uid": teacher_uid}).to_list(length=None)
        subject_ids = [s.get("_id") for s in subjects if s.get("_id")]
        if not subject_ids:
            return []

        subject_names = {str(s["_id"]): s.get("name", "Unknown") for s in subjects if s.get("_id")}

        tasks = await tasks_collection.find(
            {"subject_id": {"$in": subject_ids}}
        ).to_list(length=None)

        def _sort_key(t: dict):
            d = t.get("deadline")
            return (d is None, d or datetime.max)

        tasks.sort(key=_sort_key)
        tasks = tasks[:limit]

        result: List[Dict[str, Any]] = []
        for task in tasks:
            deadline = task.get("deadline")
            result.append(
                {
                    "task_id": str(task.get("_id")) if task.get("_id") else None,
                    "title": task.get("title", "Untitled"),
                    "subject": subject_names.get(str(task.get("subject_id")), "Unknown"),
                    "deadline": deadline.strftime("%Y-%m-%d %H:%M") if deadline else "No deadline",
                    "points": task.get("points", 0),
                    "type": task.get("task_type", "general"),
                }
            )

        return result

    async def _get_student_recent_submissions(self, user_uid: str, limit: int = 5) -> List[Dict]:
        """Get student's recent submissions"""
        submissions_collection = get_collection("submissions")
        tasks_collection = get_collection("tasks")

        submissions = await submissions_collection.find(
            {"student_uid": user_uid}
        ).sort("submitted_at", -1).limit(limit).to_list(length=limit)

        if not submissions:
            return []

        # Get task titles
        task_ids = [s.get("task_id") for s in submissions if s.get("task_id")]
        tasks = await tasks_collection.find(
            {"_id": {"$in": task_ids}}
        ).to_list(length=None)
        task_titles = {str(t["_id"]): t.get("title", "Unknown") for t in tasks}

        result = []
        for sub in submissions:
            evaluation = sub.get("evaluation", {})
            result.append({
                "task_title": task_titles.get(str(sub.get("task_id")), "Unknown"),
                "submitted_at": sub.get("submitted_at", datetime.utcnow()).strftime("%Y-%m-%d"),
                "score": sub.get("score"),
                "ai_score": evaluation.get("ai_score"),
                "status": evaluation.get("status", "pending")
            })

        return result

    async def _get_teacher_recent_submissions(self, teacher_uid: str, limit: int = 5) -> List[Dict]:
        """Get most recent submissions for tasks in teacher's classrooms"""
        subjects_collection = get_collection("subjects")
        tasks_collection = get_collection("tasks")
        submissions_collection = get_collection("submissions")

        subjects = await subjects_collection.find({"teacher_uid": teacher_uid}).to_list(length=None)
        subject_ids = [s.get("_id") for s in subjects if s.get("_id")]
        if not subject_ids:
            return []

        tasks = await tasks_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=None)
        task_ids = [t.get("_id") for t in tasks if t.get("_id")]
        if not task_ids:
            return []

        submissions = await submissions_collection.find({"task_id": {"$in": task_ids}}).sort(
            "submitted_at", -1
        ).limit(limit).to_list(length=limit)
        if not submissions:
            return []

        task_titles = {str(t.get("_id")): t.get("title", "Unknown") for t in tasks if t.get("_id")}

        result: List[Dict[str, Any]] = []
        for sub in submissions:
            evaluation = sub.get("evaluation", {}) or {}
            score = sub.get("score")
            status = evaluation.get("status", "pending")
            result.append(
                {
                    "task_title": task_titles.get(str(sub.get("task_id")), "Unknown"),
                    "student_uid": sub.get("student_uid"),
                    "submitted_at": sub.get("submitted_at", datetime.utcnow()).strftime("%Y-%m-%d"),
                    "score": score,
                    "status": status,
                }
            )

        return result

    async def _get_schedule(self, user_uid: str, limit: int = 5) -> List[Dict]:
        """Get user's prioritized task schedule"""
        from app.ai.task_scheduler import TaskScheduler

        scheduler = TaskScheduler()
        schedule = await scheduler.generate_schedule(user_uid)

        result = []
        for scheduled_task in schedule.tasks[:limit]:
            task = scheduled_task.task
            result.append({
                "title": task.title,
                "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else "No deadline",
                "points": task.points or 0,
                "priority": round(scheduled_task.priority, 2),
                "band": scheduled_task.band
            })

        return result

    async def _get_teacher_overview_schedule(self, teacher_uid: str, limit: int = 5) -> List[Dict]:
        """Lightweight teacher 'schedule' based on upcoming task deadlines."""
        tasks = await self._get_teacher_tasks(teacher_uid, limit=limit)
        result: List[Dict[str, Any]] = []
        for t in tasks[:limit]:
            deadline = t.get("deadline") or "No deadline"
            result.append(
                {
                    "title": t.get("title", "Untitled"),
                    "deadline": deadline,
                    "points": t.get("points", 0),
                    "priority": None,
                    "band": "normal",
                }
            )
        return result

    async def _get_workload(self, user_uid: str) -> Dict[str, Any]:
        """Get user's current workload metrics"""
        from app.ai.context_manager import ContextManager

        context_manager = ContextManager()
        workload = await context_manager.get_workload(user_uid)

        return {
            "pending": workload.get("pending_count", 0),
            "overdue": workload.get("overdue_count", 0),
            "due_soon": workload.get("due_soon_count", 0)
        }

    async def _get_teacher_workload(self, teacher_uid: str) -> Dict[str, Any]:
        """Get teacher workload metrics (e.g., ungraded submissions)."""
        subjects_collection = get_collection("subjects")
        tasks_collection = get_collection("tasks")
        submissions_collection = get_collection("submissions")

        subjects = await subjects_collection.find({"teacher_uid": teacher_uid}).to_list(length=None)
        subject_ids = [s.get("_id") for s in subjects if s.get("_id")]
        if not subject_ids:
            return {"ungraded_submissions": 0, "active_classrooms": 0}

        tasks = await tasks_collection.find({"subject_id": {"$in": subject_ids}}).to_list(length=None)
        task_ids = [t.get("_id") for t in tasks if t.get("_id")]
        if not task_ids:
            return {"ungraded_submissions": 0, "active_classrooms": len(subject_ids)}

        ungraded = await submissions_collection.count_documents(
            {"task_id": {"$in": task_ids}, "score": None}
        )

        return {"ungraded_submissions": int(ungraded), "active_classrooms": len(subject_ids)}

    def _fallback_response(self, intent: ChatIntent, context: Dict, role: str) -> str:
        """Generate a fallback response without Groq"""
        tasks = context.get("tasks", []) or []
        submissions = context.get("submissions", []) or []
        workload = context.get("workload", {}) or {}

        if intent == ChatIntent.OUT_OF_SCOPE:
            return "I couldn't answer that right now. Please try again in a moment."

        if intent == ChatIntent.TASK_INFO:
            tasks = context.get("tasks", [])
            if tasks:
                task_list = "\n".join([
                    f"- {t.get('title', 'Untitled')} ({t.get('subject', 'Subject')}): due {t.get('deadline', 'No deadline')}, {t.get('points', 0)} points"
                    for t in tasks[:5]
                ])
                return f"Here are your upcoming tasks:\n{task_list}"
            if role == "teacher":
                return "I couldn't find any tasks in your classrooms yet. Create a classroom and add tasks, then ask me again."
            return "You don't have any upcoming tasks."
        
        if intent == ChatIntent.GENERAL_QUERY:
            if role == "teacher":
                return "Ask me about tasks in your classrooms, upcoming deadlines, or submissions that need grading."
            return "Ask me about your tasks, deadlines, or your submission status."

        elif intent == ChatIntent.SUBMISSION_STATUS:
            submissions = context.get("submissions", [])
            if submissions:
                sub_list = "\n".join([
                    (
                        f"- {s.get('task_title', 'Task')}: "
                        f"{'graded' if s.get('score') is not None else 'pending'}"
                        + (f" (score: {s.get('score')})" if s.get('score') is not None else "")
                    )
                    for s in submissions[:5]
                ])
                return f"Here are your recent submissions:\n{sub_list}"
            if role == "teacher":
                ungraded = workload.get("ungraded_submissions")
                if isinstance(ungraded, int) and ungraded > 0:
                    return f"You have {ungraded} submissions that still need grading. Open a task to review submissions."
            return "You don't have any recent submissions."

        elif intent == ChatIntent.SCHEDULE_HELP:
            schedule = context.get("schedule", [])
            if schedule:
                task_list = "\n".join([
                    f"- {t['title']}: {t['band']} priority"
                    for t in schedule[:5]
                ])
                return f"Based on your deadlines and points, here's what you should prioritize:\n{task_list}"
            return "You don't have any pending tasks to prioritize."

        if role == "teacher":
            ungraded = workload.get("ungraded_submissions")
            if isinstance(ungraded, int) and ungraded > 0:
                return f"You have {ungraded} submissions waiting to be graded. Ask: “show my ungraded submissions” or “what tasks are due soon?”"
            return "Ask me about tasks in your classrooms, deadlines, or submissions to grade."

        pending = workload.get("pending")
        overdue = workload.get("overdue")
        if isinstance(pending, int) or isinstance(overdue, int):
            return f"Ask me about your tasks and deadlines. Right now: pending={pending or 0}, overdue={overdue or 0}."
        return "I can help you with your tasks, deadlines, and submissions. What would you like to know?"

    def _add_to_history(
        self,
        user_uid: str,
        role: str,
        content: str,
        intent: str = None
    ):
        """Add message to conversation history"""
        if user_uid not in self._history:
            self._history[user_uid] = []

        self._history[user_uid].append({
            "role": role,
            "content": content,
            "intent": intent,
            "timestamp": datetime.now(timezone.utc)
        })

        # Keep only last 20 messages per user
        if len(self._history[user_uid]) > 20:
            self._history[user_uid] = self._history[user_uid][-20:]

    def get_history(self, user_uid: str) -> List[Dict]:
        """Get conversation history for a user"""
        return self._history.get(user_uid, [])

    def clear_history(self, user_uid: str):
        """Clear conversation history for a user"""
        if user_uid in self._history:
            del self._history[user_uid]


# Factory function
_CHAT_SERVICE_INSTANCE: Optional[ChatService] = None


def get_chat_service(db: AsyncIOMotorDatabase) -> ChatService:
    """Get chat service instance with database connection"""
    global _CHAT_SERVICE_INSTANCE
    if _CHAT_SERVICE_INSTANCE is None:
        _CHAT_SERVICE_INSTANCE = ChatService(db)
    return _CHAT_SERVICE_INSTANCE
