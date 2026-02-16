import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import auth, subjects, tasks, submissions, groups, extensions, ai_assistant, dashboard, profile_pictures, ai_evaluation, quizzes, push
from app.config import settings
from app.database.connection import close_mongo_connection, connect_to_mongo, ensure_mongo_indexes
from app.utils.firebase_verify import initialize_firebase

logger = logging.getLogger(__name__)


def _parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


async def _on_startup() -> None:
    initialize_firebase()
    mongo_required = settings.mongodb_required
    if os.getenv("MONGODB_REQUIRED") is None and settings.debug:
        mongo_required = False
    try:
        await connect_to_mongo()
        if not settings.mongodb_skip_indexes:
            await ensure_mongo_indexes()
    except Exception as exc:
        if mongo_required:
            raise
        logger.error("MongoDB initialization failed: %s", exc)


async def _on_shutdown() -> None:
    await close_mongo_connection()


app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_event_handler("startup", _on_startup)
app.add_event_handler("shutdown", _on_shutdown)

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
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["quizzes"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(profile_pictures.router, prefix="/api/profile-pictures", tags=["profile_pictures"])
app.include_router(push.router, prefix="/api/push", tags=["push"])


@app.get("/health")
async def health():
    return "OK"
