"""Safe, provider-native Greenhouse job detail extraction."""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_INVALID_DETAIL_URL, ERR_INVALID_PAYLOAD, ERR_RECORD_NOT_FOUND,
)

logger = logging.getLogger(__name__)
_ALLOWED_HOSTS = {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io", "boards-api.greenhouse.io"}
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def _configured_token(config: object) -> Optional[str]:
    if not isinstance(config, dict):
        return None
    for key in ("greenhouse_token", "token", "board_token"):
        value = config.get(key)
        if isinstance(value, str) and _TOKEN_RE.fullmatch(value):
            return value
    for key in ("board_url", "target_url"):
        value = config.get(key)
        parsed = parse_greenhouse_detail_url(value) if isinstance(value, str) else None
        if parsed:
            return parsed[0]
        if isinstance(value, str):
            url = urlparse(value)
            if url.hostname in _ALLOWED_HOSTS:
                parts = [part for part in url.path.split("/") if part]
                if url.hostname == "boards-api.greenhouse.io" and len(parts) >= 3 and parts[:3] == ["v1", "boards", parts[2]]:
                    return parts[2] if _TOKEN_RE.fullmatch(parts[2]) else None
                if parts and _TOKEN_RE.fullmatch(parts[0]):
                    return parts[0]
    return None


def parse_greenhouse_detail_url(public_url: str, provider_config: object = None) -> Optional[Tuple[str, str]]:
    """Return a reviewed Greenhouse board token and numeric job id, never an arbitrary host."""
    if not isinstance(public_url, str):
        return None
    parsed = urlparse(public_url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in _ALLOWED_HOSTS:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    token = job_id = None
    if parsed.hostname in {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}:
        if len(parts) >= 3 and parts[1] == "jobs":
            token, job_id = parts[0], parts[2]
    elif len(parts) >= 5 and parts[:3] == ["v1", "boards", parts[2]] and parts[3] == "jobs":
        token, job_id = parts[2], parts[4]
    # gh_jid URLs are usable only with an explicitly reviewed token in config.
    if not job_id:
        gh_jid = parse_qs(parsed.query).get("gh_jid", [None])[0]
        token, job_id = _configured_token(provider_config), gh_jid
    if not (isinstance(token, str) and _TOKEN_RE.fullmatch(token) and isinstance(job_id, str) and job_id.isdigit()):
        return None
    return token, job_id


def build_greenhouse_detail_url(token: str, job_id: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"


async def fetch_greenhouse_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid

    parsed = parse_greenhouse_detail_url(req.public_url, req.provider_config)
    if not parsed:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    token, job_id = parsed
    try:
        response = await client.get(build_greenhouse_detail_url(token, job_id), headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        logger.info("Greenhouse detail request failed for %s: %s", token, exc)
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code == 404:
        return DetailResult.empty(ERR_RECORD_NOT_FOUND)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    try:
        data = response.json()
    except ValueError:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    if not isinstance(data, dict):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = clean_html_to_text(content)[:40000]
    if not description_is_valid(description, title=req.title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    location = data.get("location")
    location = location.get("name") if isinstance(location, dict) else None
    return DetailResult(
        description=description, title=data.get("title") if isinstance(data.get("title"), str) else None,
        location=location.strip()[:200] if isinstance(location, str) and location.strip() else None,
        source="greenhouse_api",
    )
