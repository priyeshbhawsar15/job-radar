from dataclasses import dataclass
import hashlib
import logging
import asyncio
import html
import json
import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Iterator, List, Mapping

from job_radar.config import settings
from job_radar.services.browser import BrowserServiceClient
from job_radar.services.detail_contracts import DetailRequest, DetailResult, ERR_INVALID_DETAIL_URL
from job_radar.services.oracle_detail import fetch_oracle_detail
from job_radar.services.phenom_detail import fetch_phenom_detail
from job_radar.services.workday_detail import fetch_workday_detail
from job_radar.services.zoho_detail import fetch_zoho_detail_from_html
from job_radar.services.talent500_detail import fetch_talent500_detail
from job_radar.services.greenhouse_detail import fetch_greenhouse_detail
from job_radar.services.smartrecruiters_detail import fetch_smartrecruiters_detail

logger = logging.getLogger(__name__)

REJECTION_MARKERS = [
    "window.vanityurlenabled",
    "page not found. - oracle careers",
    "candidate experience page careers",
    "accessibility assistance",
    "sorry! we couldn’t find any jobs",
    "sorry! we couldn't find any jobs",
    "full job description for ",
    "position for ",
    ".job-details-wrapper",
    "privacy policy",
    "terms of use",
]

CONTENT_INDICATORS = [
    "responsibilities",
    "qualifications",
    "requirements",
    "experience",
    "skills",
    "what you will do",
    "what you'll do",
    "what you’ll do",
    "what you will need",
    "what you'll need",
    "what you’ll need",
    "about the role",
    "job description",
    "duties",
    "role overview",
]


def _is_job_posting_type(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() == "jobposting"
    return isinstance(value, list) and any(_is_job_posting_type(item) for item in value)


def iter_json_ld_nodes(value: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from iter_json_ld_nodes(item)
    elif isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, (dict, list)):
            yield from iter_json_ld_nodes(graph)


def extract_job_posting(raw_html: str) -> Optional[Dict[str, Any]]:
    if not raw_html:
        return None
    unescaped = html.unescape(raw_html)
    script_blocks = re.findall(
        r'<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        unescaped,
        re.DOTALL | re.IGNORECASE,
    )
    for raw in script_blocks:
        try:
            data = json.loads(raw.strip())
            for node in iter_json_ld_nodes(data):
                if _is_job_posting_type(node.get("@type")):
                    if node.get("description"):
                        return node
        except Exception:
            pass
    return None


def description_is_valid(text: Optional[str], *, title: str = "") -> bool:
    if not text or not isinstance(text, str):
        return False
    cleaned = text.strip()
    if not cleaned or len(cleaned) < 200:
        return False

    low = cleaned.lower()
    if any(marker in low for marker in REJECTION_MARKERS):
        return False

    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    has_boundaries = len(lines) >= 3 or "\n\n" in cleaned or "<p>" in text.lower() or "<li>" in text.lower()
    indicator_count = sum(1 for ind in CONTENT_INDICATORS if ind in low)

    return (has_boundaries or len(cleaned) > 500) and indicator_count >= 2


def clean_html_to_text(raw_html_str: str) -> str:
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
    clean = re.sub(
        r'<(script|style|svg|iframe|noscript|nav|footer|header)\b[^>]*>[\s\S]*?</\1>',
        ' ',
        text,
        flags=re.IGNORECASE,
    )
    plain = re.sub(r'<[^>]+>', '\n', clean)
    lines = [l.strip() for l in plain.splitlines() if len(l.strip()) > 8]
    filtered = [
        l for l in lines
        if not any(x in l.lower() for x in [
            'cookie', 'gtag', 'datalayer', 'window.', 'self.', 'scrollrestoration',
            '--bprogress', 'privacy policy', 'terms of use', 'sign in', 'apply now',
            'all rights reserved', 'javascript:'
        ])
    ]
    return "\n\n".join(filtered)


def strip_to_plain_text(raw_html_str: str) -> str:
    """Strip all JS/CSS/HTML tags, returning bare plain text (last-resort before Job Ops inference)."""
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
    text = re.sub(r'<(script|style)\b[^>]*>[\s\S]*?</\1>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


class DetailExtractor:
    """Service to fetch full job detail content and parse description, salary, department & employment type."""

    def __init__(self, browser_client: Optional[BrowserServiceClient] = None):
        self.browser_client = browser_client or BrowserServiceClient()

    async def fetch_and_enrich(
        self,
        public_apply_url: str,
        board_name: str,
        title: str,
        *,
        family: str = "generic",
        provider_config: Optional[Mapping[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> DetailResult:
        provider_config = provider_config or {}
        if isinstance(provider_config, dict):
            if family == "oracle" and "oracle_detail" in provider_config and isinstance(provider_config["oracle_detail"], dict):
                provider_config = provider_config["oracle_detail"]
            elif family == "phenom" and "phenom_detail" in provider_config and isinstance(provider_config["phenom_detail"], dict):
                provider_config = provider_config["phenom_detail"]

        req = DetailRequest(
            family=family,
            public_url=public_apply_url,
            board_name=board_name,
            title=title,
            provider_config=provider_config,
        )

        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
            close_client = True

        try:
            if family == "oracle":
                return await fetch_oracle_detail(req, client)
            elif family == "phenom":
                return await fetch_phenom_detail(req, client)
            elif family == "talent500":
                return await fetch_talent500_detail(req, client)
            elif family == "google_careers":
                try:
                    raw_html = await self.browser_client.fetch_board_html(public_apply_url)
                    infer_result = await self.fetch_jobops_infer_fallback(raw_html, client)
                    if infer_result is not None:
                        return infer_result
                except Exception as e:
                    logger.info(f"Google careers infer fallback failed: {e}")
                return DetailResult.empty(ERR_INVALID_DETAIL_URL)
            elif family == "workday":
                result = await fetch_workday_detail(req, client)
                if result.error_code is None:
                    return result
                # Fall through to generic HTML fallback below on CXS failure.
            elif family == "zoho":
                raw_html = await self.browser_client.fetch_board_html(
                    public_apply_url, wait_for_selector="div.cw-jobdescription"
                )
                return fetch_zoho_detail_from_html(raw_html, public_apply_url)
            elif family == "greenhouse":
                result = await fetch_greenhouse_detail(req, client)
                if result.error_code is None:
                    return result
                # A bounded provider-native failure may still have a usable public page.
            elif family == "smartrecruiters":
                result = await fetch_smartrecruiters_detail(req, client)
                if result.error_code is None:
                    return result
                # A bounded provider-native failure may still have a usable public page.

            # Generic fallback logic
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            try:
                resp = await client.get(public_apply_url, headers=headers)
                if resp.status_code == 200 and len(resp.text) > 800:
                    parsed = self.parse_detail_html(resp.text, board_name, title, public_apply_url)
                    if parsed.get("description"):
                        return DetailResult(
                            description=parsed["description"],
                            location=parsed.get("location"),
                            employment_type=parsed.get("employment_type"),
                            department=parsed.get("department"),
                            salary_raw=parsed.get("salary_raw"),
                            salary_min=parsed.get("salary_min"),
                            salary_max=parsed.get("salary_max"),
                            salary_currency=parsed.get("salary_currency"),
                            source="generic_static_html",
                        )
            except Exception:
                pass

            raw_html = None
            try:
                raw_html = await self.browser_client.fetch_board_html(public_apply_url)
                parsed = self.parse_detail_html(raw_html, board_name, title, public_apply_url)
                if parsed.get("description"):
                    return DetailResult(
                        description=parsed["description"],
                        location=parsed.get("location"),
                        employment_type=parsed.get("employment_type"),
                        department=parsed.get("department"),
                        salary_raw=parsed.get("salary_raw"),
                        salary_min=parsed.get("salary_min"),
                        salary_max=parsed.get("salary_max"),
                        salary_currency=parsed.get("salary_currency"),
                        source="generic_browser_html",
                    )
            except Exception as e:
                logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")

            if raw_html:
                infer_result = await self.fetch_jobops_infer_fallback(raw_html, client)
                if infer_result is not None:
                    return infer_result

            return DetailResult.empty(ERR_INVALID_DETAIL_URL)

        finally:
            if close_client:
                await client.aclose()

    async def fetch_jobops_infer_fallback(
        self, raw_html_or_text: str, client: httpx.AsyncClient
    ) -> Optional[DetailResult]:
        """Fall back to Job Ops' /api/manual-jobs/infer when local deterministic parsing fails."""
        if not settings.JOBOPS_ENDPOINT:
            return None

        stripped_text = strip_to_plain_text(raw_html_or_text)[:35000]
        if not stripped_text:
            return None

        infer_url = f"{settings.JOBOPS_ENDPOINT.rstrip('/')}/api/manual-jobs/infer"
        headers = {}

        if settings.JOBOPS_USERNAME and settings.JOBOPS_PASSWORD:
            login_url = f"{settings.JOBOPS_ENDPOINT.rstrip('/')}/api/auth/login"
            try:
                login_resp = await client.post(
                    login_url,
                    json={
                        "username": settings.JOBOPS_USERNAME,
                        "password": settings.JOBOPS_PASSWORD,
                    },
                )
                if login_resp.status_code == 200:
                    login_data = login_resp.json()
                    token = (
                        login_data.get("data", {}).get("token")
                        or login_data.get("token")
                    )
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
            except Exception as e:
                logger.info(f"Job Ops auth login failed: {e}")

        try:
            resp = await client.post(
                infer_url,
                json={"jobDescription": stripped_text},
                headers=headers,
            )
        except Exception as e:
            logger.info(f"Job Ops infer fallback request failed: {e}")
            return None

        if resp.status_code != 200:
            logger.info(f"Job Ops infer fallback returned status {resp.status_code}")
            return None

        try:
            data = resp.json()
        except Exception as e:
            logger.info(f"Job Ops infer fallback returned invalid JSON: {e}")
            return None

        payload_data = data.get("data") if isinstance(data.get("data"), dict) else data
        job_data = payload_data.get("job") if isinstance(payload_data.get("job"), dict) else payload_data

        inferred_description = job_data.get("jobDescription")
        if not description_is_valid(inferred_description):
            return None

        salary_raw = job_data.get("salary")

        return DetailResult(
            description=inferred_description[:40000],
            location=(job_data.get("location") or None),
            employment_type=(job_data.get("jobType") or None),
            department=(job_data.get("department") or None),
            salary_raw=salary_raw,
            title=(job_data.get("title") or None),
            source="jobops_infer_fallback",
        )

    def parse_detail_html(self, raw_html_text: str, board_name: str, title: str, apply_url: str) -> Dict[str, Any]:
        raw_html_text = html.unescape(raw_html_text)
        jp = extract_job_posting(raw_html_text)
        if jp and jp.get("description"):
            desc_clean = clean_html_to_text(jp["description"])[:40000]
            if description_is_valid(desc_clean, title=title):
                loc = None
                job_loc = jp.get("jobLocation")
                if isinstance(job_loc, dict):
                    addr = job_loc.get("address", {})
                    if isinstance(addr, dict):
                        locality = addr.get("addressLocality")
                        region = addr.get("addressRegion")
                        country = addr.get("addressCountry")
                        parts = [p for p in [locality, region, country] if p and isinstance(p, str)]
                        if parts:
                            loc = ", ".join(parts)[:200]
                elif isinstance(job_loc, list) and len(job_loc) > 0:
                    first_loc = job_loc[0]
                    if isinstance(first_loc, dict):
                        addr = first_loc.get("address", {})
                        if isinstance(addr, dict):
                            locality = addr.get("addressLocality")
                            region = addr.get("addressRegion")
                            country = addr.get("addressCountry")
                            parts = [p for p in [locality, region, country] if p and isinstance(p, str)]
                            if parts:
                                loc = ", ".join(parts)[:200]

                emp_type = jp.get("employmentType")
                if isinstance(emp_type, list):
                    emp_type = ", ".join(str(x) for x in emp_type)
                elif not isinstance(emp_type, str):
                    emp_type = None

                sal_raw = None
                sal_min = None
                sal_max = None
                sal_curr = None
                base_sal = jp.get("baseSalary")
                if isinstance(base_sal, dict):
                    val = base_sal.get("value", {})
                    sal_curr = base_sal.get("currency")
                    if isinstance(val, dict):
                        sal_min = val.get("minValue")
                        sal_max = val.get("maxValue")
                        if sal_min and sal_max:
                            sal_raw = f"{sal_min} - {sal_max} {sal_curr or ''}".strip()
                        elif sal_min:
                            sal_raw = f"{sal_min} {sal_curr or ''}".strip()

                return {
                    "description": desc_clean,
                    "location": loc,
                    "employment_type": emp_type,
                    "department": None,
                    "salary_raw": sal_raw,
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "salary_currency": sal_curr,
                }

        # Fallback to meta tags
        desc_meta = None
        desc_match = re.search(r'<meta\b[^>]*?\bname=["\']description["\'][^>]*?\bcontent=["\'](.*?)["\']', raw_html_text, re.IGNORECASE)
        if not desc_match:
            desc_match = re.search(r'<meta\b[^>]*?\bproperty=["\']og:description["\'][^>]*?\bcontent=["\'](.*?)["\']', raw_html_text, re.IGNORECASE)

        if desc_match:
            desc_meta = html.unescape(desc_match.group(1)).strip()
            desc_clean = clean_html_to_text(desc_meta)[:40000]
            if description_is_valid(desc_clean, title=title):
                return {
                    "description": desc_clean,
                    "location": None,
                    "employment_type": None,
                    "department": None,
                    "salary_raw": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                }

        return {}

detail_extractor = DetailExtractor()
