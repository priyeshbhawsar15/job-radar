import json

import pytest
import httpx
from httpx import AsyncClient
from unittest.mock import patch

from job_radar.services import settings_store
from job_radar.config import settings as app_config


@pytest.fixture(autouse=True)
def isolated_settings_file(tmp_path, monkeypatch):
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(settings_store, "DEFAULT_CONFIG_PATH", path)
    monkeypatch.setattr(app_config, "JOBOPS_ENDPOINT", None)
    monkeypatch.setattr(app_config, "HANDOFF_ENABLED", False)
    return path


@pytest.mark.asyncio
async def test_get_settings_returns_defaults(client: AsyncClient):
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_enabled"] is False
    assert data["scheduler_interval_hours"] is None
    assert data["selected_board_ids"] == []
    assert data["handoff_enabled"] is False
    assert data["jobops_endpoint"] is None


@pytest.mark.asyncio
async def test_patch_settings_updates_and_persists(client: AsyncClient, isolated_settings_file):
    resp = await client.patch(
        "/api/v1/settings",
        json={
            "scheduler_enabled": True,
            "scheduler_interval_hours": 12,
            "selected_board_ids": ["board-google", "board-meta"],
            "handoff_enabled": True,
            "jobops_endpoint": "http://192.168.2.201:3005",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_enabled"] is True
    assert data["scheduler_interval_hours"] == 12
    assert data["selected_board_ids"] == ["board-google", "board-meta"]
    assert data["handoff_enabled"] is True
    assert data["jobops_endpoint"] == "http://192.168.2.201:3005"

    assert isolated_settings_file.exists()
    persisted = json.loads(isolated_settings_file.read_text())
    assert persisted["scheduler_interval_hours"] == 12
    assert persisted["selected_board_ids"] == ["board-google", "board-meta"]

    # A subsequent GET reflects persisted state.
    resp2 = await client.get("/api/v1/settings")
    assert resp2.json()["scheduler_interval_hours"] == 12


@pytest.mark.asyncio
async def test_patch_settings_partial_update_preserves_other_fields(client: AsyncClient):
    await client.patch(
        "/api/v1/settings",
        json={"scheduler_interval_hours": 6, "selected_board_ids": ["board-a"]},
    )
    resp = await client.patch("/api/v1/settings", json={"handoff_enabled": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_interval_hours"] == 6
    assert data["selected_board_ids"] == ["board-a"]
    assert data["handoff_enabled"] is True


_ORIGINAL_ASYNC_CLIENT_POST = httpx.AsyncClient.post


def _login_post_patch(mock_response=None, side_effect=None):
    """Only intercepts calls to the Job Ops login endpoint; other AsyncClient.post
    calls (e.g. the test client's own requests) are forwarded to the real method."""

    async def _fake_post(self, url, *args, **kwargs):
        if "auth/login" in str(url):
            if side_effect is not None:
                raise side_effect
            return mock_response
        return await _ORIGINAL_ASYNC_CLIENT_POST(self, url, *args, **kwargs)

    return _fake_post


@pytest.mark.asyncio
async def test_test_jobops_endpoint_connected(client: AsyncClient):
    await client.patch("/api/v1/settings", json={"jobops_endpoint": "http://mock-jobops.local"})

    mock_response = httpx.Response(
        status_code=200,
        json={"ok": True, "data": {"token": "abc123"}},
        request=httpx.Request("POST", "http://mock-jobops.local/api/auth/login"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_login_post_patch(mock_response=mock_response),
    ):
        resp = await client.post("/api/v1/settings/test-jobops")
    assert resp.status_code == 200
    assert resp.json()["status"] == "connected"
    assert resp.json()["detail"] == "Authentication successful"


@pytest.mark.asyncio
async def test_test_jobops_endpoint_ok_without_token_is_unreachable(client: AsyncClient):
    await client.patch("/api/v1/settings", json={"jobops_endpoint": "http://mock-jobops.local"})

    mock_response = httpx.Response(
        status_code=200,
        json={"ok": True},
        request=httpx.Request("POST", "http://mock-jobops.local/api/auth/login"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_login_post_patch(mock_response=mock_response),
    ):
        resp = await client.post("/api/v1/settings/test-jobops")
    assert resp.status_code == 200
    assert resp.json()["status"] != "connected"


@pytest.mark.asyncio
async def test_test_jobops_endpoint_uses_request_payload_over_stored(client: AsyncClient):
    await client.patch("/api/v1/settings", json={"jobops_endpoint": "http://stored.local"})

    mock_response = httpx.Response(
        status_code=200,
        json={"ok": True, "data": {"token": "abc123"}},
        request=httpx.Request("POST", "http://override.local/api/auth/login"),
    )

    seen_urls = []

    async def _fake_post(self, url, *args, **kwargs):
        if "override.local" in str(url):
            seen_urls.append(str(url))
            return mock_response
        return await _ORIGINAL_ASYNC_CLIENT_POST(self, url, *args, **kwargs)

    with patch("job_radar.api.v1.settings.httpx.AsyncClient.post", new=_fake_post):
        resp = await client.post(
            "/api/v1/settings/test-jobops",
            json={
                "jobops_endpoint": "http://override.local",
                "jobops_username": "user",
                "jobops_password": "pass",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "connected"
    assert seen_urls == ["http://override.local/api/auth/login"]


@pytest.mark.asyncio
async def test_test_jobops_endpoint_unauthorized(client: AsyncClient):
    await client.patch("/api/v1/settings", json={"jobops_endpoint": "http://mock-jobops.local"})

    mock_response = httpx.Response(
        status_code=401,
        json={"ok": False},
        request=httpx.Request("POST", "http://mock-jobops.local/api/auth/login"),
    )
    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_login_post_patch(mock_response=mock_response),
    ):
        resp = await client.post("/api/v1/settings/test-jobops")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unauthorized"
    assert resp.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_test_jobops_endpoint_unreachable(client: AsyncClient):
    await client.patch("/api/v1/settings", json={"jobops_endpoint": "http://mock-jobops.local"})

    with patch(
        "job_radar.api.v1.settings.httpx.AsyncClient.post",
        new=_login_post_patch(side_effect=httpx.ConnectError("connection refused")),
    ):
        resp = await client.post("/api/v1/settings/test-jobops")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unreachable"


@pytest.mark.asyncio
async def test_test_jobops_endpoint_not_configured(client: AsyncClient):
    resp = await client.post("/api/v1/settings/test-jobops")
    assert resp.status_code == 400
