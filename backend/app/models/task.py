from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


TaskKind = Literal["individual", "group"]
ComparisonMode = Literal["exact", "normalized", "regex", "contains"]
SandboxSecurityMode = Literal["warn", "block"]
CodeLanguage = Literal["python", "javascript", "java"]


class TaskGroupSettings(BaseModel):
    group_size: int = Field(ge=2, le=50)
    shuffle: bool = True


class CodeTestCase(BaseModel):
    input: str = ""
    expected_output: str
    timeout_ms: Optional[int] = Field(default=None, ge=50, le=30000)
    comparison_mode: ComparisonMode = "exact"
    points: int = Field(default=1, ge=0, le=100)
    description: str = Field(default="", max_length=200)


class CodeEvaluationConfig(BaseModel):
    language: CodeLanguage = "python"
    timeout_ms: int = Field(default=2000, ge=50, le=30000)
    memory_limit_mb: int = Field(default=256, ge=32, le=2048)
    max_output_kb: int = Field(default=64, ge=1, le=1024)
    enable_quality_checks: bool = True
    security_mode: SandboxSecurityMode = "warn"
    weight: float = Field(default=0.7, ge=0.0, le=1.0)
    test_cases: list[CodeTestCase] = Field(default_factory=list, max_length=200)


class DocumentEvaluationConfig(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=200)
    min_words: Optional[int] = Field(default=None, ge=0, le=20000)
    enable_readability: bool = True
    enable_plagiarism: bool = False
    enable_structure: bool = True
    weight: float = Field(default=0.3, ge=0.0, le=1.0)


class QuizQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=4)
    correct_answer: int = Field(ge=0, le=3)
    explanation: Optional[str] = Field(default=None, max_length=500)
    difficulty: Optional[str] = Field(default="medium", max_length=20)
    points: int = Field(default=1, ge=1, le=10)


class QuizEvaluationConfig(BaseModel):
    questions: list[QuizQuestion] = Field(default_factory=list, max_length=50)
    time_limit_minutes: int = Field(default=30, ge=5, le=180)
    enable_fullscreen: bool = True
    enable_anti_cheating: bool = True
    shuffle_questions: bool = True
    shuffle_options: bool = True
    passing_score: int = Field(default=60, ge=0, le=100)


class TaskEvaluationConfig(BaseModel):
    code: Optional[CodeEvaluationConfig] = None
    document: Optional[DocumentEvaluationConfig] = None
    quiz: Optional[QuizEvaluationConfig] = None


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
    evaluation_config: Optional[TaskEvaluationConfig] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    deadline: Optional[datetime] = None
    points: Optional[int] = Field(default=None, ge=0)
    task_type: Optional[str] = Field(default=None, max_length=32)
    type: Optional[TaskKind] = None
    problem_statements: Optional[list[str]] = None
    group_settings: Optional[TaskGroupSettings] = None
    evaluation_config: Optional[TaskEvaluationConfig] = None


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
    evaluation_config: Optional[TaskEvaluationConfig] = None
    created_at: datetime
    updated_at: datetime


class TaskEvaluationsSummaryResponse(BaseModel):
    task_id: str
    total_submissions: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    average_ai_score: float | None = None
