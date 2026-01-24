from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


EvaluationStatus = Literal["pending", "running", "completed", "failed"]


class TestCaseResult(BaseModel):
    case_number: int
    description: str = ""
    points: int = 1
    status: Literal["passed", "failed", "timeout", "runtime_error", "error"] = "pending"
    output: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    error: Optional[str] = None
    stderr: Optional[str] = None


class CodeEvaluationResults(BaseModel):
    passed: int = 0
    failed: int = 0
    total_points: int = 0
    earned_points: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    test_results: list[TestCaseResult] = Field(default_factory=list)


class DocumentMetrics(BaseModel):
    word_count: int = 0
    keywords_found: list[str] = Field(default_factory=list)
    readability_score: Optional[float] = None
    plagiarism_detected: bool = False
    structure_quality: Optional[float] = None


class QuizAnswer(BaseModel):
    question_index: int
    selected_option: int
    is_correct: bool = False
    points_earned: int = 0


class MalpracticeEvent(BaseModel):
    event_type: Literal["tab_switch", "window_blur", "exit_fullscreen", "copy_paste", "right_click", "other"]
    timestamp: datetime
    details: Optional[str] = None


class QuizAttemptMetrics(BaseModel):
    answers: list[QuizAnswer] = Field(default_factory=list)
    total_questions: int = 0
    correct_answers: int = 0
    total_points: int = 0
    earned_points: int = 0
    score_percentage: float = 0.0
    time_started: Optional[datetime] = None
    time_submitted: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    malpractice_events: list[MalpracticeEvent] = Field(default_factory=list)
    malpractice_detected: bool = False
    locked_out: bool = False


class SubmissionEvaluation(BaseModel):
    status: EvaluationStatus = "pending"
    code_results: CodeEvaluationResults = Field(default_factory=CodeEvaluationResults)
    document_metrics: DocumentMetrics = Field(default_factory=DocumentMetrics)
    quiz_metrics: Optional[QuizAttemptMetrics] = None
    ai_score: Optional[int] = Field(default=None, ge=0, le=100)
    ai_feedback: Optional[str] = Field(default=None, max_length=10000)
    evaluated_at: Optional[datetime] = None
    last_error: Optional[str] = Field(default=None, max_length=2000)


class BatchEvaluateRequest(BaseModel):
    task_id: str


class BatchEvaluateResponse(BaseModel):
    queued: int


class EvaluationProgressResponse(BaseModel):
    status: EvaluationStatus
    progress: int = Field(ge=0, le=100)
    message: str
    ai_score: Optional[int] = Field(default=None, ge=0, le=100)
    error: Optional[str] = None


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


class QuizSubmitRequest(BaseModel):
    task_id: str
    answers: list[int] = Field(min_length=1, max_length=50)
    time_taken_seconds: int = Field(ge=0, le=10800)
    malpractice_events: list[MalpracticeEvent] = Field(default_factory=list)


class QuizGenerateRequest(BaseModel):
    document_content: str = Field(min_length=1, max_length=50000)
    topic: str = Field(min_length=1, max_length=200)
    num_questions: int = Field(ge=5, le=50, default=10)
