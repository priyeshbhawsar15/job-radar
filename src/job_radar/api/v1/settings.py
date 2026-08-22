from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from job_radar.config import settings as app_config
from job_radar.services.settings_store import load_settings, save_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsResponse(BaseModel):
    scheduler_enabled: bool
    scheduler_interval_hours: Optional[int] = None
    selected_board_ids: List[str] = []
    handoff_enabled: bool
    jobops_endpoint: Optional[str] = None
    jobops_username: Optional[str] = None
    jobops_password: Optional[str] = None
    discord_webhook_enabled: bool = False
    discord_webhook_url: str = ""


class UpdateSettingsRequest(BaseModel):
    scheduler_enabled: Optional[bool] = None
    scheduler_interval_hours: Optional[int] = None
    selected_board_ids: Optional[List[str]] = None
    handoff_enabled: Optional[bool] = None
    jobops_endpoint: Optional[str] = None
    jobops_username: Optional[str] = None
    jobops_password: Optional[str] = None
    discord_webhook_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None


class TestJobOpsResponse(BaseModel):
    status: str
    detail: Optional[str] = None


class TestDiscordWebhookResponse(BaseModel):
    ok: bool
    message: str


def _to_response(stored) -> SettingsResponse:
    return SettingsResponse(
        scheduler_enabled=stored.scheduler_enabled,
        scheduler_interval_hours=stored.scheduler_interval_hours,
        selected_board_ids=stored.selected_board_ids,
        handoff_enabled=stored.handoff_enabled,
        jobops_endpoint=stored.jobops_endpoint or app_config.JOBOPS_ENDPOINT,
        jobops_username=stored.jobops_username,
        jobops_password=stored.jobops_password,
        discord_webhook_enabled=stored.discord_webhook_enabled,
        discord_webhook_url=stored.discord_webhook_url,
    )


@router.get("", response_model=SettingsResponse)
async def get_settings():
    stored = load_settings()
    return _to_response(stored)


@router.patch("", response_model=SettingsResponse)
async def update_settings(req: UpdateSettingsRequest):
    stored = load_settings()
    update_data = req.model_dump(exclude_unset=True)
    updated = stored.model_copy(update=update_data)
    save_settings(updated)

    app_config.HANDOFF_ENABLED = updated.handoff_enabled
    if updated.jobops_endpoint:
        app_config.JOBOPS_ENDPOINT = updated.jobops_endpoint

    return _to_response(updated)


@router.post("/test-jobops", response_model=TestJobOpsResponse)
async def test_jobops_connection():
    stored = load_settings()
    endpoint = stored.jobops_endpoint or app_config.JOBOPS_ENDPOINT
    username = stored.jobops_username or app_config.JOBOPS_USERNAME
    password = stored.jobops_password or app_config.JOBOPS_PASSWORD
    if not endpoint:
        raise HTTPException(status_code=400, detail="Job Ops endpoint not configured")

    url = f"{endpoint.rstrip('/')}/api/auth/login"
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            resp = await http_client.post(
                url, json={"username": username, "password": password}
            )
    except httpx.RequestError as exc:
        return TestJobOpsResponse(status="unreachable", detail=str(exc))

    try:
        body = resp.json()
    except ValueError:
        body = {}

    if resp.status_code == 200 and body.get("ok") is True:
        return TestJobOpsResponse(status="connected", detail="Authentication successful")
    if resp.status_code in (401, 403) or body.get("ok") is False:
        return TestJobOpsResponse(status="unauthorized", detail="Invalid credentials")
    if resp.status_code >= 500 or resp.status_code == 404:
        return TestJobOpsResponse(status="unreachable", detail=f"HTTP {resp.status_code}")
    return TestJobOpsResponse(status="connected")


@router.post("/test-discord-webhook", response_model=TestDiscordWebhookResponse)
async def test_discord_webhook():
    stored = load_settings()
    if not stored.discord_webhook_url:
        raise HTTPException(status_code=400, detail="Discord webhook URL not configured")

    payload = {
        "embeds": [
            {
                "title": "🎯 Job Radar Discord Webhook Test Connection",
                "color": 0x10B981,
                "description": "This is a test notification from Job Radar's Settings page.",
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(stored.discord_webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return TestDiscordWebhookResponse(ok=False, message=f"Failed to reach Discord webhook: {exc}")

    return TestDiscordWebhookResponse(ok=True, message="Test notification delivered to Discord successfully!")
