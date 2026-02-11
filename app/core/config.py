from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "clowbot"
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"

    # In unit tests / CI we avoid long startup retries against external deps.
    ENSURE_EXTERNAL_DEPS_ON_STARTUP: bool = True

    ADMIN_TOKEN: str = "change-me-admin-token"
    AUTH_DISABLED: bool = False

    DATABASE_URL: str

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "memory"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "clowbot"
    MINIO_SECURE: bool = False

    # Optional integrations (STUB by default)
    TELEGRAM_BOT_TOKEN: str | None = None
    # Comma-separated allowlist of chat ids/usernames (e.g. "@mychannel,123456789")
    TELEGRAM_ALLOWLIST_CHATS: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
