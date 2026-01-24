from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_db_name: str = Field(default="task_scheduling_agent", alias="MONGODB_DB_NAME")
    mongodb_server_selection_timeout_ms: int = Field(
        default=5000, alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS"
    )

    # Application Settings
    app_name: str = Field(default="Task Scheduling Agent V2", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", alias="ALLOWED_ORIGINS"
    )

    # File Upload Configuration
    uploads_dir: str = Field(default="uploads", alias="UPLOADS_DIR")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")

    # Firebase Configuration
    firebase_credentials_path: Optional[str] = Field(
        default="./firebase-credentials.json", alias="FIREBASE_CREDENTIALS_PATH"
    )
    firebase_credentials_base64: Optional[str] = Field(
        default=None, alias="FIREBASE_CREDENTIALS_BASE64"
    )

    # Groq AI Configuration
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    groq_enable_routing: bool = Field(default=True, alias="GROQ_ENABLE_ROUTING")
    groq_enable_guards: bool = Field(default=True, alias="GROQ_ENABLE_GUARDS")
    groq_enable_caching: bool = Field(default=True, alias="GROQ_ENABLE_CACHING")
    groq_cache_ttl_seconds: int = Field(default=3600, alias="GROQ_CACHE_TTL_SECONDS")
    groq_global_rpm: int = Field(default=30, alias="GROQ_GLOBAL_RPM")
    groq_global_rpd: int = Field(default=14000, alias="GROQ_GLOBAL_RPD")
    groq_teacher_weight: int = Field(default=2, alias="GROQ_TEACHER_WEIGHT")
    groq_student_weight: int = Field(default=1, alias="GROQ_STUDENT_WEIGHT")
    groq_teacher_count: int = Field(default=40, alias="GROQ_TEACHER_COUNT")
    groq_student_count: int = Field(default=100, alias="GROQ_STUDENT_COUNT")

    # Redis Configuration (for Groq caching)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
