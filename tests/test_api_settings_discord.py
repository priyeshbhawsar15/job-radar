import pytest
import httpx
from httpx import AsyncClient
from unittest.mock import patch

from job_radar.services import settings_store
from job_radar.config import settings as app_config


@pytest.fixture(autouse=True)
def isolated_settings_file(tmp_path, monkeypatch):
    monkeypatch.delenv("SETTINGS_FILE_PATH", raising=False)
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(settings_store, "DEFAULT_CONFIG_PATH", path)
    monkeypatch.setattr(app_config, "JOBOPS_ENDPOINT", None)
    monkeypatch.setattr(app_config, "HANDOFF_ENABLED", False)
    return path


_ORIGINAL_ASYNC_CLIENT_POST = httpx.AsyncClient.post


def _webhook_post_patch(mock_response=None, side_effect=None):
    """Only intercepts calls to the Discord webhook URL; other AsyncClient.post
    calls (e.g. the test client's own requests) are forwarded to the real method."""

    async def _fake_post(self, url, *args, **kwargs):
        if "discord.com" in str(url):
            if side_effect is not None:
                raise side_effect
            return mock_response
        return await _ORIGINAL_ASYNC_CLIENT_POST(self, url, *args, **kwargs)

    return _fake_post


@pytest.mark.asyncio
async def test_test_discord_webhook_empty_url_returns_ok_false(client: AsyncClient):
    resp = await client.post("/api/v1/settings/test-discord-webhook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["message"] == "Discord Webhook URL is empty. Please enter a valid URL."


@pytest.mark.asyncio
async def test_test_discord_webhook_success(client: AsyncClient):
    await client.patch(
        "/api/v1/settings",
        json={"discord_webhook_url": "https://discord.com/api/webhooks/123/abc"},
    )

    mock_response = httpx.Response(
        status_code=204,
        request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_webhook_post_patch(mock_response=mock_response),
    ):
        resp = await client.post("/api/v1/settings/test-discord-webhook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["message"] == "Test notification delivered to Discord successfully!"


@pytest.mark.asyncio
async def test_test_discord_webhook_http_status_error(client: AsyncClient):
    await client.patch(
        "/api/v1/settings",
        json={"discord_webhook_url": "https://discord.com/api/webhooks/123/abc"},
    )

    mock_response = httpx.Response(
        status_code=404,
        request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_webhook_post_patch(mock_response=mock_response),
    ):
        resp = await client.post("/api/v1/settings/test-discord-webhook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["message"] == "Webhook test failed: HTTP 404"


@pytest.mark.asyncio
async def test_test_discord_webhook_uses_request_payload_without_saved_settings(client: AsyncClient):
    mock_response = httpx.Response(
        status_code=204,
        request=httpx.Request("POST", "https://discord.com/api/webhooks/999/unsaved"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_webhook_post_patch(mock_response=mock_response),
    ):
        resp = await client.post(
            "/api/v1/settings/test-discord-webhook",
            json={"discord_webhook_url": "https://discord.com/api/webhooks/999/unsaved"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["message"] == "Test notification delivered to Discord successfully!"


@pytest.mark.asyncio
async def test_test_discord_webhook_request_error(client: AsyncClient):
    await client.patch(
        "/api/v1/settings",
        json={"discord_webhook_url": "https://discord.com/api/webhooks/123/abc"},
    )

    exc = httpx.ConnectError("connection refused")
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_webhook_post_patch(side_effect=exc),
    ):
        resp = await client.post("/api/v1/settings/test-discord-webhook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["message"] == f"Webhook test failed: {exc}"
