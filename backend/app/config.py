from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_db_name: str = Field(default="task_scheduling_agent", alias="MONGODB_DB_NAME")
    mongodb_server_selection_timeout_ms: int = Field(
        default=5000, alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS"
    )

    app_name: str = Field(default="Task Scheduling Agent V2", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", alias="ALLOWED_ORIGINS"
    )

    uploads_dir: str = Field(default="uploads", alias="UPLOADS_DIR")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
