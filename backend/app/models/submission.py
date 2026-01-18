from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


EvaluationStatus = Literal["pending", "running", "completed", "failed"]


class CodeEvaluationResults(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)


class DocumentMetrics(BaseModel):
    word_count: int = 0
    keywords_found: list[str] = Field(default_factory=list)


class SubmissionEvaluation(BaseModel):
    status: EvaluationStatus = "pending"
    code_results: CodeEvaluationResults = Field(default_factory=CodeEvaluationResults)
    document_metrics: DocumentMetrics = Field(default_factory=DocumentMetrics)
    ai_score: Optional[int] = Field(default=None, ge=0, le=100)
    ai_feedback: Optional[str] = Field(default=None, max_length=10000)
    evaluated_at: Optional[datetime] = None
    last_error: Optional[str] = Field(default=None, max_length=2000)


class BatchEvaluateRequest(BaseModel):
    task_id: str


class BatchEvaluateResponse(BaseModel):
    queued: int


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
    evaluation: Optional[SubmissionEvaluation] = None
    attachments: list[SubmissionAttachmentResponse] = Field(default_factory=list)
