"""
AI Assistant API Routes

Provides endpoints for:
- User context management
- AI task scheduling
- Chat assistant with credit system
"""

import logging
from fastapi import APIRouter, Depends, Response, HTTPException, status

from app.ai.context_manager import ContextManager
from app.ai.task_scheduler import TaskScheduler
from app.models.context import AIScheduleResponse, UserContext, UserContextUpdateRequest
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistory,
    ChatMessage,
    ChatClearResponse,
    CreditStatus,
    CreditResetRequest,
    CreditResetResponse,
)
from app.services.chat_service import get_chat_service
from app.services.credit_service import CreditService
from app.utils.dependencies import get_current_user, get_current_student, get_current_teacher
from app.database.connection import get_database

logger = logging.getLogger(__name__)

router = APIRouter()
_context_manager = ContextManager()
_task_scheduler = TaskScheduler(context_manager=_context_manager)


# ========================================
# Helper functions
# ========================================

def _get_credit_service():
    """Get credit service instance"""
    db = get_database()
    return CreditService(db)


def _get_chat_service():
    """Get chat service instance"""
    db = get_database()
    return get_chat_service(db)


@router.get("/context", response_model=UserContext)
async def get_context(current_student: dict = Depends(get_current_student)):
    return await _context_manager.get_user_context(current_student["uid"])


@router.patch("/context", response_model=UserContext)
async def patch_context(
    request: UserContextUpdateRequest,
    current_student: dict = Depends(get_current_student),
):
    return await _context_manager.update_context(current_student["uid"], request)


@router.get("/schedule", response_model=AIScheduleResponse)
async def get_schedule(response: Response, current_student: dict = Depends(get_current_student)):
    response.headers["Cache-Control"] = "no-store"
    return await _task_scheduler.generate_schedule(current_student["uid"])


@router.post("/schedule/optimize", response_model=AIScheduleResponse)
async def optimize_schedule(response: Response, current_student: dict = Depends(get_current_student)):
    response.headers["Cache-Control"] = "no-store"
    return await _task_scheduler.generate_schedule(current_student["uid"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai_assistant"}


# ========================================
# Chat Assistant Endpoints
# ========================================

@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message to the chat assistant.

    The assistant can help with:
    - Task information and deadlines
    - Submission status and grades
    - Scheduling and prioritization

    Deducts 1 credit per message. Returns error if no credits remaining.
    """
    user_uid = current_user["uid"]
    role = current_user.get("role", "student")

    chat_service = _get_chat_service()

    try:
        result = await chat_service.process_message(
            user_uid=user_uid,
            role=role,
            message=request.message
        )

        # Check for error codes
        if result.get("error") == "NO_CREDITS":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": result["response"],
                    "error_code": "NO_CREDITS",
                    "credits_remaining": 0
                }
            )

        return ChatResponse(
            response=result["response"],
            intent=result["intent"],
            context_used=result.get("context_used", []),
            credits_remaining=result["credits_remaining"],
            timestamp=result.get("timestamp")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for user {user_uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/chat/history", response_model=ChatHistory)
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the current user's chat history.

    History is stored in-memory per session (not persisted).
    """
    user_uid = current_user["uid"]
    chat_service = _get_chat_service()

    history = chat_service.get_history(user_uid)

    messages = [
        ChatMessage(
            role=msg["role"],
            content=msg["content"],
            intent=msg.get("intent"),
            timestamp=msg.get("timestamp")
        )
        for msg in history
    ]

    return ChatHistory(
        messages=messages,
        total_messages=len(messages)
    )


@router.delete("/chat/clear", response_model=ChatClearResponse)
async def clear_chat_history(
    current_user: dict = Depends(get_current_user),
):
    """
    Clear the current user's chat history.
    """
    user_uid = current_user["uid"]
    chat_service = _get_chat_service()

    chat_service.clear_history(user_uid)

    return ChatClearResponse(
        success=True,
        message="Chat history cleared"
    )


# ========================================
# Credit System Endpoints
# ========================================

@router.get("/credits", response_model=CreditStatus)
async def get_credits(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the current user's credit status.

    Shows remaining messages, daily limit, and reset time.
    """
    user_uid = current_user["uid"]
    role = current_user.get("role", "student")

    credit_service = _get_credit_service()

    try:
        status_data = await credit_service.get_credits(user_uid, role)

        return CreditStatus(
            credits_remaining=status_data["credits_remaining"],
            credits_limit=status_data["credits_limit"],
            credits_used=status_data["credits_used"],
            resets_at=status_data["resets_at"]
        )

    except Exception as e:
        logger.error(f"Credit status error for user {user_uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get credit status"
        )


@router.post("/credits/reset", response_model=CreditResetResponse)
async def reset_credits(
    request: CreditResetRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    """
    Reset credits for a specific user (teacher/admin only).

    This is an administrative function to manually reset a student's
    daily message limit.
    """
    credit_service = _get_credit_service()

    try:
        # Use provided role or default to student
        role = request.role or "student"

        result = await credit_service.reset_credits(request.user_uid, role)

        if result["success"]:
            return CreditResetResponse(
                success=True,
                message=f"Credits reset for user {request.user_uid}"
            )
        else:
            return CreditResetResponse(
                success=False,
                message=result.get("error", "Failed to reset credits")
            )

    except Exception as e:
        logger.error(f"Credit reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset credits"
        )
