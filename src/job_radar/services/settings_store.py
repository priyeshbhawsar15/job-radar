import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, field_validator

from job_radar.services.scheduler_alignment import ALLOWED_INTERVAL_HOURS, DEFAULT_ANCHOR_TIME, is_valid_anchor_time

DEFAULT_CONFIG_PATH = Path("app_settings.json")


def _get_config_path() -> Path:
    env_path = os.getenv("SETTINGS_FILE_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


class AppSettingsModel(BaseModel):
    scheduler_enabled: bool = False
    scheduler_interval_hours: Optional[int] = None
    scheduler_anchor_time: str = DEFAULT_ANCHOR_TIME
    selected_board_ids: List[str] = []
    handoff_enabled: bool = False
    jobops_endpoint: Optional[str] = None
    jobops_username: Optional[str] = None
    jobops_password: Optional[str] = None
    discord_webhook_enabled: bool = False
    discord_webhook_url: str = ""
    global_browser_concurrency: int = 10
    jobops_import_batch_size: int = 50

    @field_validator("scheduler_anchor_time")
    @classmethod
    def _validate_anchor_time(cls, value: str) -> str:
        if not is_valid_anchor_time(value):
            raise ValueError(
                f"scheduler_anchor_time must be a strict HH:mm value (00:00-23:59), got {value!r}"
            )
        return value

    @field_validator("scheduler_interval_hours")
    @classmethod
    def _validate_interval_hours(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in ALLOWED_INTERVAL_HOURS:
            raise ValueError(
                f"scheduler_interval_hours must be one of {ALLOWED_INTERVAL_HOURS} or None, got {value!r}"
            )
        return value


def load_settings(path: Path = None) -> AppSettingsModel:
    path = path or _get_config_path()
    if path.exists():
        try:
            return AppSettingsModel(**json.loads(path.read_text()))
        except (json.JSONDecodeError, ValueError):
            return AppSettingsModel()
    return AppSettingsModel()


def save_settings(model: AppSettingsModel, path: Path = None) -> None:
    path = path or _get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2))
