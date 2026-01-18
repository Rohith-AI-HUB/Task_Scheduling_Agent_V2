from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from app.models.user import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    UserCreate,
)
from app.utils.firebase_verify import verify_firebase_token, get_firebase_user
from app.utils.dependencies import get_current_user
from app.database.collections import get_collection

router = APIRouter()


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token UID does not match request UID"
            )

        # Check if user already exists
        users_collection = get_collection("users")
        existing_user = await users_collection.find_one(
            {"uid": request.uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )

        if existing_user:
            return UserResponse(**existing_user)

        # Validate role
        if request.role not in ["teacher", "student"]:
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
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        try:
            await users_collection.insert_one(user_data)
        except DuplicateKeyError:
            created_user = await users_collection.find_one(
                {"uid": request.uid},
                sort=[("updated_at", -1), ("_id", -1)],
            )
            if created_user:
                return UserResponse(**created_user)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        created_user = await users_collection.find_one(
            {"uid": request.uid},
            sort=[("updated_at", -1), ("_id", -1)],
        )
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        return UserResponse(**created_user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
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
            if request.role not in ["teacher", "student"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role is required for first-time login (teacher or student)"
                )

            # Get user data from Firebase if not provided in request
            if not request.email or not request.name:
                firebase_user = await get_firebase_user(uid)
                email = request.email or firebase_user.email
                name = request.name or firebase_user.display_name or firebase_user.email.split("@")[0]
            else:
                email = request.email
                name = request.name

            # Create user with role from request (defaults to 'student')
            user_data = {
                "uid": uid,
                "email": email,
                "name": name,
                "role": request.role,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            try:
                await users_collection.insert_one(user_data)
            except DuplicateKeyError:
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user's information

    This endpoint requires authentication (Bearer token in Authorization header)
    """
    return UserResponse(**current_user)


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "auth"}
