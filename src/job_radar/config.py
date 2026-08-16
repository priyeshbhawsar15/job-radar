from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Radar"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./job_radar.db"

    # Security / Secret
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Browser Service
    BROWSER_SERVICE_URL: str = "http://127.0.0.1:3013"

    # Job Ops Handoff
    JOBOPS_ENDPOINT: Optional[str] = None
    JOBOPS_USERNAME: Optional[str] = None
    JOBOPS_PASSWORD: Optional[str] = None
    HANDOFF_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
