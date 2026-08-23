from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Radar"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite+aiosqlite:////home/priyesh/Work/job-radar/job_radar.db"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    BROWSER_SERVICE_URL: str = "http://192.168.2.201:3013"

    JOBOPS_ENDPOINT: Optional[str] = None
    JOBOPS_USERNAME: Optional[str] = None
    JOBOPS_PASSWORD: Optional[str] = None
    HANDOFF_ENABLED: bool = False

    SETTINGS_FILE_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
