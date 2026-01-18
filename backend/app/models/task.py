from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    subject_id: str
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    deadline: Optional[datetime] = None
    points: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[str] = Field(default=None, max_length=32)


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    deadline: Optional[datetime] = None
    points: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[str] = Field(default=None, max_length=32)


class TaskResponse(BaseModel):
    id: str
    subject_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    points: Optional[int] = None
    task_type: Optional[str] = None
    type: str
    created_at: datetime
    updated_at: datetime
