from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


TaskKind = Literal["individual", "group"]


class TaskGroupSettings(BaseModel):
    group_size: int = Field(ge=2, le=50)
    shuffle: bool = True


class TaskCreateRequest(BaseModel):
    subject_id: str
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    deadline: Optional[datetime] = None
    points: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[str] = Field(default=None, max_length=32)
    type: TaskKind = "individual"
    problem_statements: list[str] = Field(default_factory=list, max_length=50)
    group_settings: Optional[TaskGroupSettings] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    deadline: Optional[datetime] = None
    points: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[str] = Field(default=None, max_length=32)
    type: Optional[TaskKind] = None
    problem_statements: Optional[list[str]] = None
    group_settings: Optional[TaskGroupSettings] = None


class TaskResponse(BaseModel):
    id: str
    subject_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    points: Optional[int] = None
    task_type: Optional[str] = None
    type: TaskKind
    problem_statements: list[str] = Field(default_factory=list)
    group_settings: Optional[TaskGroupSettings] = None
    created_at: datetime
    updated_at: datetime


class TaskEvaluationsSummaryResponse(BaseModel):
    task_id: str
    total_submissions: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    average_ai_score: float | None = None
