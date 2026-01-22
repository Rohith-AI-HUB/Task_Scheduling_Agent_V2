"""
Chat and Credit System Models
Pydantic models for the chat assistant and credit system.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ========================================
# Credit System Models
# ========================================

class CreditStatus(BaseModel):
    """Response model for credit status"""
    credits_remaining: int = Field(..., description="Number of messages remaining today")
    credits_limit: int = Field(..., description="Daily message limit")
    credits_used: int = Field(0, description="Messages used today")
    resets_at: str = Field(..., description="ISO timestamp when credits reset (midnight UTC)")


class CreditUseResponse(BaseModel):
    """Response when using a credit"""
    success: bool
    credits_remaining: int
    credits_limit: Optional[int] = None
    error: Optional[str] = None


class CreditResetRequest(BaseModel):
    """Request to reset credits (admin only)"""
    user_uid: str
    role: Optional[str] = None


class CreditResetResponse(BaseModel):
    """Response for credit reset"""
    success: bool
    message: str


# ========================================
# Chat Models
# ========================================

class ChatRequest(BaseModel):
    """Request model for chat messages"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's chat message"
    )


class ChatResponse(BaseModel):
    """Response model for chat messages"""
    response: str = Field(..., description="Assistant's response")
    intent: str = Field(..., description="Detected intent of the message")
    context_used: List[str] = Field(
        default_factory=list,
        description="Context types used to generate response"
    )
    credits_remaining: int = Field(..., description="Credits remaining after this message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


class ChatMessage(BaseModel):
    """Model for a single chat message (for history)"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    intent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistory(BaseModel):
    """Response model for chat history"""
    messages: List[ChatMessage] = Field(default_factory=list)
    total_messages: int = 0


class ChatClearResponse(BaseModel):
    """Response for clearing chat history"""
    success: bool
    message: str


# ========================================
# Error Responses
# ========================================

class ChatErrorResponse(BaseModel):
    """Error response for chat-related errors"""
    error: str
    error_code: str = "CHAT_ERROR"
    credits_remaining: Optional[int] = None


class RateLimitResponse(BaseModel):
    """Response when rate limit is exceeded"""
    error: str = "Rate limit exceeded"
    error_code: str = "RATE_LIMIT"
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retrying"
    )


class NoCreditsResponse(BaseModel):
    """Response when user has no credits"""
    error: str = "Daily message limit reached"
    error_code: str = "NO_CREDITS"
    credits_remaining: int = 0
    resets_at: str = Field(..., description="When credits reset")
