from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: str


class UserCreate(BaseModel):
    """User creation model"""
    uid: str = Field(..., description="Firebase UID")
    email: EmailStr
    name: str
    role: str = Field(default="student", description="User role: teacher or student")


class UserLogin(BaseModel):
    """User login model"""
    idToken: str = Field(..., description="Firebase ID token")


class UserResponse(BaseModel):
    """User response model"""
    uid: str
    email: str
    name: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Decoded token data"""
    uid: Optional[str] = None
    email: Optional[str] = None


class RegisterRequest(BaseModel):
    """Registration request model"""
    uid: str
    email: EmailStr
    name: str
    idToken: str
    role: str = Field(default="student", pattern="^(teacher|student)$")


class LoginRequest(BaseModel):
    """Login request model"""
    idToken: str
    # Optional fields for Google Sign-In with role selection
    uid: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(teacher|student)$")
