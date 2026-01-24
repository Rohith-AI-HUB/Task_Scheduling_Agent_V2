from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import auth, subjects, tasks, submissions, groups, extensions, ai_assistant, dashboard, profile_pictures, ai_evaluation
from app.config import settings
from app.database.connection import close_mongo_connection, connect_to_mongo, ensure_mongo_indexes
from app.utils.firebase_verify import initialize_firebase


def _parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK
    initialize_firebase()
    # Connect to MongoDB
    await connect_to_mongo()
    await ensure_mongo_indexes()
    yield
    # Cleanup
    await close_mongo_connection()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(subjects.router, prefix="/api/subjects", tags=["subjects"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
app.include_router(extensions.router, prefix="/api/extensions", tags=["extensions"])
app.include_router(ai_assistant.router, prefix="/api/ai", tags=["ai"])
app.include_router(ai_evaluation.router, prefix="/api/ai-eval", tags=["ai_evaluation"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(profile_pictures.router, prefix="/api/profile-pictures", tags=["profile_pictures"])


@app.get("/health")
async def health():
    return {"status": "ok"}
