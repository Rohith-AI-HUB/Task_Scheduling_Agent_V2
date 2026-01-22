from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.task import TaskResponse

WorkloadPreference = Literal["heavy", "balanced", "light"]
ReminderFrequency = Literal["off", "daily", "weekly"]
PriorityBand = Literal["urgent", "high", "normal", "low"]


class TaskCompletionPattern(BaseModel):
    average_time_hours: Optional[float] = Field(default=None, ge=0)
    preferred_hours: list[int] = Field(default_factory=list)
    peak_productivity: Optional[str] = Field(default=None, max_length=32)


class UserContext(BaseModel):
    user_uid: str
    workload_preference: WorkloadPreference = Field(default="balanced")
    reminder_frequency: ReminderFrequency = Field(default="daily")
    task_completion_pattern: TaskCompletionPattern = Field(default_factory=TaskCompletionPattern)
    created_at: datetime
    updated_at: datetime


class UserContextUpdateRequest(BaseModel):
    workload_preference: Optional[WorkloadPreference] = None
    reminder_frequency: Optional[ReminderFrequency] = None
    task_completion_pattern: Optional[TaskCompletionPattern] = None


class ScheduledTask(BaseModel):
    task: TaskResponse
    priority: float = Field(ge=0)
    band: PriorityBand
    explanation: Optional[str] = Field(
        default=None,
        description="AI-generated explanation for why this task has this priority"
    )


class AIScheduleResponse(BaseModel):
    generated_at: datetime
    tasks: list[ScheduledTask] = Field(default_factory=list)
    has_explanations: bool = Field(
        default=False,
        description="Whether AI explanations are included"
    )

