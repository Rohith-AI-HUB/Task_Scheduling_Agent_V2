from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: Optional[str] = Field(default=None, min_length=1, max_length=32)


class SubjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    code: Optional[str] = Field(default=None, min_length=1, max_length=32)


class JoinSubjectRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=16)


class SubjectResponse(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    teacher_uid: str
    join_code: str
    created_at: datetime
    updated_at: datetime
