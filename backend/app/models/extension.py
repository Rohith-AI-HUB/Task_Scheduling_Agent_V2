"""
Extension Request Models
Handles deadline extension requests from students with AI workload analysis
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ExtensionAIAnalysis(BaseModel):
    """AI-generated workload analysis for extension request"""

    workload_score: float = Field(..., ge=0, le=1, description="Workload intensity score (0=light, 1=heavy)")
    recommendation: str = Field(..., description="AI recommendation (approve, deny, partial)")
    reasoning: str = Field(..., description="Detailed explanation of the recommendation")
    current_workload: dict = Field(..., description="Current workload snapshot")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    suggested_extension_days: Optional[int] = Field(None, description="AI-suggested extension duration in days")


class ExtensionRequestCreate(BaseModel):
    """Request body for creating an extension request"""

    task_id: str = Field(..., description="Task ID for which extension is requested")
    requested_deadline: datetime = Field(..., description="Requested new deadline")
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for extension request")


class ExtensionRequestResponse(BaseModel):
    """Extension request response model"""

    id: str = Field(..., description="Extension request ID")
    student_uid: str = Field(..., description="Student UID who requested")
    student_name: Optional[str] = Field(None, description="Student display name")
    task_id: str = Field(..., description="Task ID")
    task_title: Optional[str] = Field(None, description="Task title")
    subject_id: Optional[str] = Field(None, description="Subject ID")
    subject_name: Optional[str] = Field(None, description="Subject name")
    current_deadline: datetime = Field(..., description="Current task deadline")
    requested_deadline: datetime = Field(..., description="Requested new deadline")
    extension_days: int = Field(..., description="Number of days extension requested")
    reason: str = Field(..., description="Student's reason for extension")
    status: str = Field(..., description="Request status: pending, approved, denied")
    ai_analysis: Optional[ExtensionAIAnalysis] = Field(None, description="AI workload analysis")
    teacher_response: Optional[str] = Field(None, description="Teacher's response/notes")
    reviewed_by: Optional[str] = Field(None, description="Teacher UID who reviewed")
    created_at: datetime = Field(..., description="Request creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")


class ExtensionRequestList(BaseModel):
    """List of extension requests with pagination"""

    items: List[ExtensionRequestResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of requests")
    pending_count: int = Field(0, description="Number of pending requests")
    approved_count: int = Field(0, description="Number of approved requests")
    denied_count: int = Field(0, description="Number of denied requests")


class ExtensionReviewRequest(BaseModel):
    """Request body for reviewing (approving/denying) an extension"""

    response: Optional[str] = Field(None, max_length=500, description="Teacher's response/notes")
    approved_deadline: Optional[datetime] = Field(None, description="Approved deadline (if different from requested)")


class ExtensionReviewResponse(BaseModel):
    """Response after reviewing an extension request"""

    success: bool
    message: str
    extension: ExtensionRequestResponse


class ExtensionStats(BaseModel):
    """Extension request statistics"""

    total_requests: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    denied_requests: int = 0
    approval_rate: float = 0.0
    average_extension_days: float = 0.0


class WorkloadSnapshot(BaseModel):
    """Snapshot of student's current workload for AI analysis"""

    pending_tasks: int
    overdue_tasks: int
    upcoming_deadlines: List[dict]  # List of tasks due in next 7 days
    recent_submissions: int  # Submissions in last 7 days
    average_submission_time: Optional[float]  # Average hours before deadline
    current_subjects: int
    total_points_at_stake: int
