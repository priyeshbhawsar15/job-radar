"""Direct Philips static job detail extraction and HTTP payload fetching."""

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
    ERR_RECORD_NOT_FOUND,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)


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


def description_is_valid(desc: Optional[str]) -> bool:
    if not desc or len(desc) < 50:
        return False
    lower = desc.lower()
    markers = [
        "window.vanityurlenabled",
        "candidate experience page careers",
        "accessibility assistance",
        "sorry! we couldn’t find any jobs",
        "sorry! we couldn't find any jobs",
        "cookie preferences",
        "privacy policy",
        "terms of use",
        "gtag",
        "datalayer",
        "javascript:",
    ]
    if any(m in lower for m in markers):
        return False
    return True


def extract_job_posting_json_ld(raw_html: str) -> Optional[dict]:
    if not raw_html:
        return None
    matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html, re.DOTALL | re.IGNORECASE)
    for match in matches:
        match_str = match.strip()
        if not match_str:
            continue
        try:
            data = json.loads(match_str)
        except Exception:
            continue

        nodes = []
        if isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                nodes.extend(data["@graph"])
            else:
                nodes.append(data)
        elif isinstance(data, list):
            nodes.extend(data)

        for node in nodes:
            if not isinstance(node, dict):
                continue
            type_val = node.get("@type")
            is_job = False
            if isinstance(type_val, str) and type_val.lower() == "jobposting":
                is_job = True
            elif isinstance(type_val, list) and any(isinstance(t, str) and t.lower() == "jobposting" for t in type_val):
                is_job = True

            if is_job:
                return node
    return None


def extract_location_from_json_ld(job_node: dict) -> Optional[str]:
    job_loc = job_node.get("jobLocation")
    if not job_loc:
        return None

    if isinstance(job_loc, list) and len(job_loc) > 0:
        job_loc = job_loc[0]

    if not isinstance(job_loc, dict):
        return None

    address = job_loc.get("address")
    if not isinstance(address, dict):
        return None

    locality = address.get("addressLocality")
    region = address.get("addressRegion")
    country = address.get("addressCountry")

    parts = []
    if locality:
        parts.append(str(locality).strip())
    if region:
        parts.append(str(region).strip())
    if country:
        c_str = str(country).strip()
        if c_str == "IN":
            c_str = "India"
        elif c_str == "US":
            c_str = "United States"
        parts.append(c_str)

    deduped = []
    for p in parts:
        if p and p not in deduped:
            deduped.append(p)

    return ", ".join(deduped) if deduped else None


def extract_phenom_bounded_dom_description(raw_html: str) -> Optional[str]:
    if not raw_html:
        return None
    patterns = [
        r'<section[^>]*component-content-key=["\']description["\'][^>]*>(.*?)</section>',
        r'<section[^>]*class=["\'][^"\']*phs-job-details-area[^"\']*["\'][^>]*>(.*?)</section>',
        r'<div[^>]*class=["\'][^"\']*description-block[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\'][^"\']*job-description-ph[^"\']*["\'][^>]*>(.*?)</div>',
    ]

    for pat in patterns:
        match = re.search(pat, raw_html, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = clean_html_to_text(match.group(1))
            if description_is_valid(cleaned):
                return cleaned
    return None


def extract_phenom_posting(raw_html: str, title: str = "") -> DetailResult:
    if not raw_html:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)

    node = extract_job_posting_json_ld(raw_html)
    if node:
        raw_desc = node.get("description") or ""
        cleaned_desc = clean_html_to_text(raw_desc)
        if description_is_valid(cleaned_desc):
            if len(cleaned_desc) > 40_000:
                cleaned_desc = cleaned_desc[:40_000].strip()
            loc = extract_location_from_json_ld(node)
            emp_type = node.get("employmentType")
            if isinstance(emp_type, list):
                emp_type = ", ".join(str(x) for x in emp_type)
            elif emp_type:
                emp_type = str(emp_type)
            return DetailResult(
                description=cleaned_desc,
                location=loc,
                employment_type=emp_type,
                source="phenom_json_ld",
            )

    # Fallback to bounded DOM
    dom_desc = extract_phenom_bounded_dom_description(raw_html)
    if dom_desc:
        if len(dom_desc) > 40_000:
            dom_desc = dom_desc[:40_000].strip()
        return DetailResult(
            description=dom_desc,
            source="phenom_description_dom",
        )

    return DetailResult.empty(ERR_DESCRIPTION_MISSING)


async def fetch_phenom_detail(request: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    config = request.provider_config or {}
    allowed_origins = config.get("allowed_origins", [])

    if not allowed_origins:
        return DetailResult.empty(ERR_INVALID_PROVIDER_CONFIG)

    allowed_hosts = {urlparse(o if o.startswith("http") else f"https://{o}").netloc for o in allowed_origins}

    public_host = urlparse(request.public_url).netloc
    if public_host not in allowed_hosts:
        return DetailResult.empty(ERR_BOUNDARY_VIOLATION)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = await client.get(request.public_url, headers=headers)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)

    final_host = urlparse(str(resp.url)).netloc
    if final_host not in allowed_hosts:
        return DetailResult.empty(ERR_BOUNDARY_VIOLATION)

    if resp.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)

    if len(resp.content) > 5 * 1024 * 1024:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)

    return extract_phenom_posting(resp.text, request.title)
