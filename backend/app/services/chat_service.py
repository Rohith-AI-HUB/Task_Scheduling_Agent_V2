"""
Chat Service
Handles the chat assistant functionality with intent classification,
context gathering, and Groq integration.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.intent_classifier import (
    ChatIntent,
    classify_intent,
    get_required_context,
    get_greeting_response,
    get_out_of_scope_response
)
from app.services.groq_service import groq_service, RateLimitExceeded
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
        # Check credits first
        credit_result = await self.credit_service.use_credit(user_uid, role)

        if not credit_result["success"]:
            return {
                "response": credit_result["error"],
                "intent": "no_credits",
                "context_used": [],
                "credits_remaining": 0,
                "error": "NO_CREDITS"
            }

        # Classify intent
        intent, confidence = classify_intent(message)
        logger.debug(f"Classified intent: {intent} (confidence: {confidence})")

        # Handle special intents without Groq
        if intent == ChatIntent.GREETING:
            return {
                "response": get_greeting_response(),
                "intent": intent.value,
                "context_used": [],
                "credits_remaining": credit_result["credits_remaining"],
                "timestamp": datetime.utcnow().isoformat()
            }

        if intent == ChatIntent.OUT_OF_SCOPE:
            return {
                "response": get_out_of_scope_response(),
                "intent": intent.value,
                "context_used": [],
                "credits_remaining": credit_result["credits_remaining"],
                "timestamp": datetime.utcnow().isoformat()
            }

        # Gather context based on intent
        context = await self._gather_context(user_uid, intent)
        context_used = list(context.keys())

        # Generate response with Groq
        try:
            response = await groq_service.chat_response(
                user_uid=user_uid,
                message=message,
                intent=intent.value,
                context=context
            )
        except RateLimitExceeded as e:
            response = str(e)
        except Exception as e:
            logger.error(f"Chat response error: {e}")
            response = self._fallback_response(intent, context)

        # Store in history
        self._add_to_history(user_uid, "user", message, intent.value)
        self._add_to_history(user_uid, "assistant", response)

        return {
            "response": response,
            "intent": intent.value,
            "context_used": context_used,
            "credits_remaining": credit_result["credits_remaining"],
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _gather_context(
        self,
        user_uid: str,
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
                context["tasks"] = await self._get_user_tasks(user_uid)

            if "submissions" in required_context or "pending_evaluations" in required_context:
                context["submissions"] = await self._get_recent_submissions(user_uid)

            if "schedule" in required_context:
                context["schedule"] = await self._get_schedule(user_uid)

            if "workload" in required_context:
                context["workload"] = await self._get_workload(user_uid)

        except Exception as e:
            logger.error(f"Error gathering context: {e}")

        return context

    async def _get_user_tasks(self, user_uid: str, limit: int = 10) -> List[Dict]:
        """Get user's upcoming tasks"""
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
                "title": task.get("title", "Untitled"),
                "subject": subject_names.get(str(task.get("subject_id")), "Unknown"),
                "deadline": deadline.strftime("%Y-%m-%d %H:%M") if deadline else "No deadline",
                "points": task.get("points", 0),
                "type": task.get("task_type", "general")
            })

        return result

    async def _get_recent_submissions(self, user_uid: str, limit: int = 5) -> List[Dict]:
        """Get user's recent submissions"""
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

    def _fallback_response(self, intent: ChatIntent, context: Dict) -> str:
        """Generate a fallback response without Groq"""
        if intent == ChatIntent.TASK_INFO:
            tasks = context.get("tasks", [])
            if tasks:
                task_list = "\n".join([
                    f"- {t['title']}: due {t['deadline']}, {t['points']} points"
                    for t in tasks[:5]
                ])
                return f"Here are your upcoming tasks:\n{task_list}"
            return "You don't have any upcoming tasks."

        elif intent == ChatIntent.SUBMISSION_STATUS:
            submissions = context.get("submissions", [])
            if submissions:
                sub_list = "\n".join([
                    f"- {s['task_title']}: {'graded' if s['score'] else 'pending'}"
                    + (f" (score: {s['score']})" if s['score'] else "")
                    for s in submissions[:5]
                ])
                return f"Here are your recent submissions:\n{sub_list}"
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
            "timestamp": datetime.utcnow().isoformat()
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
def get_chat_service(db: AsyncIOMotorDatabase) -> ChatService:
    """Get chat service instance with database connection"""
    return ChatService(db)
