import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

DEFAULT_CONFIG_PATH = Path("app_settings.json")


class AppSettingsModel(BaseModel):
    scheduler_enabled: bool = False
    scheduler_interval_hours: Optional[int] = None
    selected_board_ids: List[str] = []
    handoff_enabled: bool = False
    jobops_endpoint: Optional[str] = None
    jobops_username: Optional[str] = None
    jobops_password: Optional[str] = None
    discord_webhook_enabled: bool = False
    discord_webhook_url: str = ""


def load_settings(path: Path = None) -> AppSettingsModel:
    path = path or DEFAULT_CONFIG_PATH
    if path.exists():
        try:
            return AppSettingsModel(**json.loads(path.read_text()))
        except (json.JSONDecodeError, ValueError):
            return AppSettingsModel()
    return AppSettingsModel()


def save_settings(model: AppSettingsModel, path: Path = None) -> None:
    path = path or DEFAULT_CONFIG_PATH
    path.write_text(model.model_dump_json(indent=2))
