"""Direct Oracle HCM detail extraction and HTTP payload fetching."""

import html
import json
import re
from typing import Any, List, Mapping, Optional, Set
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest,
    DetailResult,
    ERR_INVALID_PROVIDER_CONFIG,
    ERR_INVALID_DETAIL_URL,
    ERR_BOUNDARY_VIOLATION,
    ERR_HTTP_STATUS,
    ERR_RESPONSE_TOO_LARGE,
    ERR_INVALID_PAYLOAD,
    ERR_RECORD_NOT_FOUND,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)


def extract_oracle_public_id(public_url: str) -> Optional[str]:
    if not public_url:
        return None
    match = re.search(r"/job/(\d+)", public_url)
    return match.group(1) if match else None


def clean_html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(?:p|br|h[1-6]|div|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_for_comparison(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def find_oracle_item(payload: Mapping[str, Any], public_id: str) -> Optional[Mapping[str, Any]]:
    if not isinstance(payload, dict):
        return None
    items = payload.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and str(item.get("Id")) == str(public_id):
            return item
    return None


def compose_oracle_description(item: Mapping[str, Any]) -> Optional[str]:
    if not item or not isinstance(item, dict):
        return None

    ext_desc_raw = item.get("ExternalDescriptionStr") or ""
    ext_resp_raw = item.get("ExternalResponsibilitiesStr") or ""
    ext_qual_raw = item.get("ExternalQualificationsStr") or ""

    section_configs = [
        (None, ext_desc_raw),
        ("RESPONSIBILITIES", ext_resp_raw),
        ("QUALIFICATIONS", ext_qual_raw),
    ]

    seen_paragraphs: Set[str] = set()
    composed_parts = []

    for heading, raw_content in section_configs:
        text = clean_html_to_text(raw_content)
        if not text:
            continue
        paras = extract_paragraphs(text)
        unique_paras = []
        for p in paras:
            norm = normalize_for_comparison(p)
            if norm and norm not in seen_paragraphs:
                seen_paragraphs.add(norm)
                unique_paras.append(p)
        if unique_paras:
            sec_text = "\n".join(unique_paras)
            if heading:
                # Add heading if not already present in sec_text
                first_line = unique_paras[0].upper()
                if heading in first_line:
                    composed_parts.append(sec_text)
                else:
                    composed_parts.append(f"{heading}\n{sec_text}")
            else:
                composed_parts.append(sec_text)

    final_description = "\n\n".join(composed_parts).strip()
    if not final_description or len(final_description) < 50:
        return None
    if len(final_description) > 40_000:
        final_description = final_description[:40_000].strip()

    return final_description


async def fetch_oracle_detail(request: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    config = request.provider_config or {}
    api_origin = config.get("api_origin")
    allowed_origins = config.get("allowed_origins", [])

    if not api_origin or not allowed_origins:
        return DetailResult.empty(ERR_INVALID_PROVIDER_CONFIG)

    api_host = urlparse(api_origin).netloc
    allowed_hosts = {urlparse(o if o.startswith("http") else f"https://{o}").netloc for o in allowed_origins}

    if api_host not in allowed_hosts:
        return DetailResult.empty(ERR_INVALID_PROVIDER_CONFIG)

    public_id = extract_oracle_public_id(request.public_url)
    if not public_id:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)

    public_host = urlparse(request.public_url).netloc
    if public_host not in allowed_hosts:
        return DetailResult.empty(ERR_BOUNDARY_VIOLATION)

    endpoint = f"{api_origin}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
    site_number = config.get("site_number")
    finder_val = f'ById;Id="{public_id}"'
    if site_number:
        finder_val += f',siteNumber={site_number}'

    params = {
        "expand": "all",
        "onlyData": "true",
        "finder": finder_val,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        resp = await client.get(endpoint, params=params, headers=headers)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)

    final_host = urlparse(str(resp.url)).netloc
    if final_host not in allowed_hosts:
        return DetailResult.empty(ERR_BOUNDARY_VIOLATION)

    if resp.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)

    if len(resp.content) > 5 * 1024 * 1024:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)

    try:
        data = resp.json()
    except Exception:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    item = find_oracle_item(data, public_id)
    if not item:
        return DetailResult.empty(ERR_RECORD_NOT_FOUND)

    description = compose_oracle_description(item)
    if not description:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)

    location = item.get("PrimaryLocation")
    if location:
        location = str(location).strip()
        if re.fullmatch(r"\d+(?:, India)?", location):
            location = None

    return DetailResult(
        description=description,
        location=location,
        source="oracle_hcm_detail",
    )
