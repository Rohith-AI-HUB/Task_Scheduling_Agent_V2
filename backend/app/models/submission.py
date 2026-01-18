from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubmissionAttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime


class SubmissionUpsertRequest(BaseModel):
    task_id: str
    content: str = Field(default="", max_length=10000)
    group_id: Optional[str] = None


class SubmissionGradeRequest(BaseModel):
    score: Optional[float] = Field(default=None, ge=0)
    feedback: Optional[str] = Field(default=None, max_length=10000)


class SubmissionResponse(BaseModel):
    id: str
    task_id: str
    subject_id: str
    student_uid: str
    group_id: Optional[str] = None
    content: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
    score: Optional[float] = None
    feedback: Optional[str] = None
    attachments: list[SubmissionAttachmentResponse] = Field(default_factory=list)
