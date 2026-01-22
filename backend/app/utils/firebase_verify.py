import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, status
from app.config import settings
import os
import json
import base64
import tempfile

# Initialize Firebase Admin SDK
_firebase_app = None


def initialize_firebase():
    """Initialize Firebase Admin SDK

    Supports two methods for loading credentials:
    1. Base64 encoded JSON (for production/cloud platforms)
    2. File path (for local development)
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        cred = None

        # Method 1: Try base64 encoded credentials (production)
        if settings.firebase_credentials_base64:
            try:
                # Decode base64 credentials
                cred_json = base64.b64decode(settings.firebase_credentials_base64).decode('utf-8')
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                print("✅ Firebase credentials loaded from base64 environment variable")
            except Exception as e:
                print(f"⚠️ Failed to load base64 credentials: {e}")

        # Method 2: Try file path (development)
        if cred is None:
            # Check configured path first
            cred_path = settings.firebase_credentials_path

            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                print(f"✅ Firebase credentials loaded from: {cred_path}")
            else:
                # Try default locations
                default_paths = [
                    os.path.join(os.path.dirname(__file__), "..", "..", "firebase-credentials.json"),
                    os.path.join(os.getcwd(), "firebase-credentials.json"),
                    "./firebase-credentials.json"
                ]

                for path in default_paths:
                    if os.path.exists(path):
                        cred = credentials.Certificate(path)
                        print(f"✅ Firebase credentials loaded from: {path}")
                        break

        if cred is None:
            raise FileNotFoundError(
                "Firebase credentials not found. Please set FIREBASE_CREDENTIALS_BASE64 "
                "or place 'firebase-credentials.json' in the backend directory."
            )

        _firebase_app = firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized successfully")
        return _firebase_app

    except Exception as e:
        print(f"❌ Failed to initialize Firebase Admin SDK: {e}")
        raise


async def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token data

    Args:
        token: Firebase ID token from client

    Returns:
        dict: Decoded token with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        # Verify the token
        decoded_token = auth.verify_id_token(token)
        return decoded_token

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_firebase_user(uid: str):
    """
    Get Firebase user data by UID

    Args:
        uid: Firebase user UID

    Returns:
        UserRecord: Firebase user record
    """
    try:
        user = auth.get_user(uid)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )
