from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.firebase_verify import verify_firebase_token
from app.database.collections import get_collection
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from Firebase token

    Args:
        credentials: HTTP Authorization credentials with Bearer token

    Returns:
        dict: User data from database

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Verify Firebase token
    token_data = await verify_firebase_token(credentials.credentials)

    # Get user from database
    users_collection = get_collection("users")
    user = await users_collection.find_one(
        {"uid": token_data["uid"]},
        sort=[("updated_at", -1), ("_id", -1)],
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    return user


async def get_current_teacher(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user is a teacher

    Args:
        current_user: Current authenticated user

    Returns:
        dict: Teacher user data

    Raises:
        HTTPException: If user is not a teacher
    """
    if current_user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    return current_user


async def get_current_student(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user is a student

    Args:
        current_user: Current authenticated user

    Returns:
        dict: Student user data

    Raises:
        HTTPException: If user is not a student
    """
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, otherwise None

    Args:
        credentials: Optional HTTP Authorization credentials

    Returns:
        Optional[dict]: User data if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token_data = await verify_firebase_token(credentials.credentials)
        users_collection = get_collection("users")
        user = await users_collection.find_one(
            {"uid": token_data["uid"]},
            sort=[("updated_at", -1), ("_id", -1)],
        )
        return user
    except Exception:
        # Silently fail for optional authentication
        return None
