from fastapi import APIRouter, HTTPException, status, Depends, Query, File, UploadFile
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

from app.models.user import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    UserCreate,
)
from app.utils.firebase_verify import verify_firebase_token, get_firebase_user
from app.utils.dependencies import get_current_user, get_current_teacher
from app.database.collections import get_collection
from app.config import settings
from app.services.profile_pictures import delete_profile_picture, upsert_profile_picture

router = APIRouter()
logger = logging.getLogger(__name__)


class UserUpdateRequest(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UserListResponse(BaseModel):
    """Response model for user listing"""
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user in the database after Firebase authentication

    This endpoint is called after the user has been created in Firebase.
    It stores the user data in MongoDB.
    """
    try:
        # Verify the Firebase token
        token_data = await verify_firebase_token(request.idToken)

        # Ensure the UID matches
        if token_data["uid"] != request.uid:
            logger.warning(f"UID mismatch during registration: token={token_data['uid']}, request={request.uid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication failed"
            )

        # Check if user already exists
        users_collection = get_collection("users")
        existing_user = await users_collection.find_one(
            {"uid": request.uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )

        if existing_user:
            logger.info(f"User already registered: uid={request.uid}, email={request.email}")
            return UserResponse(**existing_user)

        # Validate role
        if request.role not in ["teacher", "student"]:
            logger.warning(f"Invalid role during registration: role={request.role}, uid={request.uid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'teacher' or 'student'"
            )

        # Create user document
        user_data = {
            "uid": request.uid,
            "email": request.email,
            "name": request.name,
            "role": request.role,
            "photo_url": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        try:
            await users_collection.insert_one(user_data)
            logger.info(f"User registered successfully: uid={request.uid}, email={request.email}, role={request.role}")
        except DuplicateKeyError:
            logger.warning(f"Duplicate key during registration: uid={request.uid}")
            created_user = await users_collection.find_one(
                {"uid": request.uid},
                sort=[("updated_at", -1), ("_id", -1)],
            )
            if created_user:
                return UserResponse(**created_user)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User registration failed"
            )

        created_user = await users_collection.find_one(
            {"uid": request.uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )
        if not created_user:
            logger.error(f"Failed to retrieve created user: uid={request.uid}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User registration failed"
            )
        return UserResponse(**created_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=UserResponse)
async def login(request: LoginRequest):
    """
    Login user by verifying Firebase token and returning user data

    This endpoint verifies the Firebase token and returns the user data from MongoDB.
    If the user doesn't exist in MongoDB (e.g., Google Sign-In), create the user.
    """
    try:
        # Verify the Firebase token
        token_data = await verify_firebase_token(request.idToken)
        uid = token_data["uid"]

        # Get user from database
        users_collection = get_collection("users")
        user = await users_collection.find_one(
            {"uid": uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )

        # If user doesn't exist, create them (for Google Sign-In)
        if not user:
            if not request.role or request.role not in ["teacher", "student"]:
                logger.warning(f"First-time login without valid role: uid={uid}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role is required for first-time login (teacher or student)"
                )

            # Get user data from Firebase if not provided in request
            if not request.email or not request.name:
                firebase_user = await get_firebase_user(uid)
                email = request.email or firebase_user.email
                name = request.name or firebase_user.display_name or firebase_user.email.split("@")[0]
                photo_url = getattr(firebase_user, "photo_url", None)
            else:
                email = request.email
                name = request.name
                photo_url = None

            # Create user with role from request
            user_data = {
                "uid": uid,
                "email": email,
                "name": name,
                "role": request.role,
                "photo_url": photo_url,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            try:
                await users_collection.insert_one(user_data)
                logger.info(f"User created during login: uid={uid}, email={email}, role={request.role}")
            except DuplicateKeyError:
                logger.warning(f"Duplicate key during login auto-registration: uid={uid}")
                user = await users_collection.find_one(
                    {"uid": uid},
                    sort=[("updated_at", -1), ("_id", -1)],
                )
            else:
                user = await users_collection.find_one(
                    {"uid": uid},
                    sort=[("updated_at", -1), ("_id", -1)],
                )

        if not user:
            logger.error(f"Login failed: user not found after creation: uid={uid}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )

        logger.info(f"User logged in: uid={uid}, role={user.get('role')}")
        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user's information

    This endpoint requires authentication (Bearer token in Authorization header)
    """
    return UserResponse(**current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current user's profile information

    Allows users to update their name and email.
    Firebase email should be updated separately through Firebase Auth.
    """
    try:
        users_collection = get_collection("users")

        # Build update document
        update_fields = {"updated_at": datetime.utcnow()}

        if update_data.name is not None:
            update_fields["name"] = update_data.name.strip()

        if update_data.email is not None:
            # Check if email is already in use by another user
            existing = await users_collection.find_one({
                "email": update_data.email,
                "uid": {"$ne": current_user["uid"]}
            })
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
            update_fields["email"] = update_data.email

        # Update user
        result = await users_collection.update_one(
            {"uid": current_user["uid"]},
            {"$set": update_fields}
        )

        if result.modified_count == 0 and result.matched_count == 0:
            logger.error(f"Failed to update user profile: uid={current_user['uid']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile update failed"
            )

        # Get updated user
        updated_user = await users_collection.find_one(
            {"uid": current_user["uid"]},
            sort=[("updated_at", -1), ("_id", -1)],
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User profile updated: uid={current_user['uid']}, fields={list(update_fields.keys())}")
        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/me/photo", response_model=UserResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        users_collection = get_collection("users")
        await upsert_profile_picture(current_user, file)

        updated_user = await users_collection.find_one(
            {"uid": current_user["uid"]},
            sort=[("updated_at", -1), ("_id", -1)],
        )
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return UserResponse(**updated_user)
    finally:
        try:
            await file.close()
        except Exception:
            pass


@router.delete("/me/photo", response_model=UserResponse)
async def delete_profile_photo(current_user: dict = Depends(get_current_user)):
    users_collection = get_collection("users")
    user = await users_collection.find_one(
        {"uid": current_user["uid"]},
        sort=[("updated_at", -1), ("_id", -1)],
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_profile_picture(current_user)
    updated_user = await users_collection.find_one(
        {"uid": current_user["uid"]},
        sort=[("updated_at", -1), ("_id", -1)],
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**updated_user)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    role: Optional[str] = Query(None, regex="^(teacher|student)$"),
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_teacher: dict = Depends(get_current_teacher)
):
    """
    List users (teachers only)

    Teachers can view all users to manage enrollments and assignments.
    Supports filtering by role and searching by name/email.
    """
    try:
        users_collection = get_collection("users")

        # Build query
        query = {}
        if role:
            query["role"] = role

        if search:
            # Case-insensitive search in name and email
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]

        # Get total count
        total = await users_collection.count_documents(query)

        # Get paginated users
        skip = (page - 1) * page_size
        users_cursor = users_collection.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        users = await users_cursor.to_list(length=page_size)

        user_responses = [UserResponse(**user) for user in users]

        logger.info(f"Users listed by teacher: uid={current_teacher['uid']}, role_filter={role}, search={search}, page={page}")

        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"List users error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get("/users/{uid}", response_model=UserResponse)
async def get_user_by_uid(
    uid: str,
    current_teacher: dict = Depends(get_current_teacher)
):
    """
    Get user by UID (teachers only)

    Allows teachers to view any user's profile for administrative purposes.
    """
    try:
        users_collection = get_collection("users")
        user = await users_collection.find_one(
            {"uid": uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by UID error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "auth"}
