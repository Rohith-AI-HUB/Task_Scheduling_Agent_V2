from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DueSoonBand = Literal["urgent", "high", "normal"]


class DueSoonItem(BaseModel):
    task_id: str
    subject_id: str
    title: str
    deadline: datetime
    band: DueSoonBand
    due_in_minutes: int
    is_overdue: bool


class DueSoonResponse(BaseModel):
    generated_at: datetime
    items: list[DueSoonItem] = Field(default_factory=list)


UpcomingBand = Literal["urgent", "high", "normal"]


class UpcomingTaskItem(BaseModel):
    task_id: str
    subject_id: str
    title: str
    deadline: datetime
    band: UpcomingBand
    due_in_minutes: int


class UpcomingTasksResponse(BaseModel):
    generated_at: datetime
    items: list[UpcomingTaskItem] = Field(default_factory=list)


class TeacherUpcomingTaskItem(BaseModel):
    task_id: str
    subject_id: str
    subject_name: str
    title: str
    deadline: datetime
    band: UpcomingBand
    due_in_minutes: int


class TeacherUpcomingTasksResponse(BaseModel):
    generated_at: datetime
    items: list[TeacherUpcomingTaskItem] = Field(default_factory=list)


class TeacherPendingSummaryResponse(BaseModel):
    generated_at: datetime
    pending_submissions: int = 0
    total_submissions: int = 0
