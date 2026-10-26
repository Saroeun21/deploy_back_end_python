from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "TripOS API"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://deoloy-front-end-python.vercel.app",
    ]
    WEBSITE_URL: str = "http://localhost:5173"

    DATABASE_URL: str = "postgresql+psycopg://tripos_user:change-me@localhost:5432/tripos_db"
    JWT_SECRET_KEY: str = "replace-this-with-a-long-random-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_EMAILS: str = ""
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    FIREBASE_PROJECT_ID: str | None = None
    GOOGLE_VISION_API_KEY: str | None = None
    GMAIL_CLIENT_ID: str | None = None
    GMAIL_CLIENT_SECRET: str | None = None
    GMAIL_REFRESH_TOKEN: str | None = None
    GMAIL_USER: str | None = None
    GMAIL_FROM_EMAIL: str | None = None
    GMAIL_FROM_NAME: str = "Komsan"
    EMAIL_WORKER_ENABLED: bool = True
    EMAIL_WORKER_INTERVAL_SECONDS: int = Field(default=60, gt=0)
    UPLOAD_DIR: Path = Path("uploads")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
