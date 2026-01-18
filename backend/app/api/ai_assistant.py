from fastapi import APIRouter, Depends

from app.ai.context_manager import ContextManager
from app.ai.task_scheduler import TaskScheduler
from app.models.context import AIScheduleResponse, UserContext, UserContextUpdateRequest
from app.utils.dependencies import get_current_student

router = APIRouter()
_context_manager = ContextManager()
_task_scheduler = TaskScheduler(context_manager=_context_manager)


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
async def get_schedule(current_student: dict = Depends(get_current_student)):
    return await _task_scheduler.generate_schedule(current_student["uid"])


@router.post("/schedule/optimize", response_model=AIScheduleResponse)
async def optimize_schedule(current_student: dict = Depends(get_current_student)):
    return await _task_scheduler.generate_schedule(current_student["uid"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai_assistant"}
