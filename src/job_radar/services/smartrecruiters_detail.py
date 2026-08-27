"""Safe, provider-native SmartRecruiters job detail extraction."""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_INVALID_DETAIL_URL, ERR_INVALID_PAYLOAD, ERR_RECORD_NOT_FOUND,
)

logger = logging.getLogger(__name__)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_POSTING_RE = re.compile(r"^[A-Za-z0-9-]{1,128}$")


def parse_smartrecruiters_detail_url(public_url: str, provider_config: object = None) -> Optional[Tuple[str, str]]:
    """Accept only SmartRecruiters canonical public posting URLs or reviewed config."""
    if not isinstance(public_url, str):
        return None
    parsed = urlparse(public_url)
    if parsed.scheme not in ("http", "https") or parsed.hostname != "jobs.smartrecruiters.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    identifier, posting_id = parts[0], parts[1]
    if not (_IDENTIFIER_RE.fullmatch(identifier) and _POSTING_RE.fullmatch(posting_id)):
        return None
    return identifier, posting_id


def build_smartrecruiters_detail_url(identifier: str, posting_id: str) -> str:
    return f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings/{posting_id}"


def _value(value: object) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("label") or value.get("name")
    return value.strip()[:200] if isinstance(value, str) and value.strip() else None


def _location(value: object) -> Optional[str]:
    if not isinstance(value, dict):
        return _value(value)
    return _value(value.get("fullLocation") or value.get("address")) or ", ".join(
        item for item in (_value(value.get("city")), _value(value.get("region")), _value(value.get("country"))) if item
    ) or None


def _section_description(sections: object) -> str:
    if not isinstance(sections, dict):
        return ""
    # Keep the actual job content and useful non-boilerplate sections in provider order.
    preferred = ("jobDescription", "qualifications", "additionalInformation", "benefits", "companyDescription")
    chunks = []
    for key in preferred:
        section = sections.get(key)
        if not isinstance(section, dict):
            continue
        text = section.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        plain = re.sub(r"<[^>]+>", " ", text).strip().lower()
        if key == "additionalInformation" and len(plain) < 180 and any(marker in plain for marker in ("eeo", "equal opportunity", "confidential")):
            continue
        heading = _value(section.get("title"))
        chunks.append(f"<h2>{heading}</h2>{text}" if heading else text)
    return "\n".join(chunks)


async def fetch_smartrecruiters_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid

    parsed = parse_smartrecruiters_detail_url(req.public_url, req.provider_config)
    if not parsed:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    identifier, posting_id = parsed
    try:
        response = await client.get(build_smartrecruiters_detail_url(identifier, posting_id), headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        logger.info("SmartRecruiters detail request failed for %s: %s", identifier, exc)
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
    job_ad = data.get("jobAd")
    content = _section_description(job_ad.get("sections") if isinstance(job_ad, dict) else None)
    if not content:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = clean_html_to_text(content)[:40000]
    if not description_is_valid(description, title=req.title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    return DetailResult(
        description=description, title=_value(data.get("name")), location=_location(data.get("location")),
        employment_type=_value(data.get("typeOfEmployment")), department=_value(data.get("function")),
        source="smartrecruiters_api",
    )
