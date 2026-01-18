from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    task_id: str
    regenerate: bool = False


class GroupResponse(BaseModel):
    id: str
    task_id: str
    subject_id: str
    group_set_id: str
    name: str
    member_uids: list[str] = Field(default_factory=list)
    assigned_problem_index: Optional[int] = None
    assigned_problem_statement: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submission_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submission_updated_at: Optional[datetime] = None
    submitted_by_uid: Optional[str] = None


class GroupListResponse(BaseModel):
    task_id: str
    group_set_id: Optional[str] = None
    group_settings: Optional[dict] = None
    problem_statements: list[str] = Field(default_factory=list)
    has_submissions: bool = False
    groups: list[GroupResponse] = Field(default_factory=list)
