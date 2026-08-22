import logging
import json
import html
import re
import httpx
from typing import Optional, Dict, Any, Iterator, List, Mapping
from job_radar.config import settings
from job_radar.services.browser import BrowserServiceClient
from job_radar.services.detail_contracts import DetailRequest, DetailResult, ERR_INVALID_DETAIL_URL
from job_radar.services.oracle_detail import fetch_oracle_detail
from job_radar.services.phenom_detail import fetch_phenom_detail
from job_radar.services.workday_detail import fetch_workday_detail
from job_radar.services.zoho_detail import fetch_zoho_detail_from_html

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

            # Greenhouse or Generic fallback logic
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            if 'gh_jid=' in public_apply_url or 'greenhouse.io' in public_apply_url:
                gh_id = None
                if 'gh_jid=' in public_apply_url:
                    gh_id = public_apply_url.split('gh_jid=')[-1].split('&')[0]
                elif '/jobs/' in public_apply_url:
                    gh_id = public_apply_url.split('/jobs/')[-1].split('?')[0]

                if gh_id and gh_id.isdigit():
                    slug = "abnormalsecurity" if 'abnormal' in board_name.lower() else ("cognite" if 'cognite' in board_name.lower() else board_name.lower().replace(' ', ''))
                    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{gh_id}"
                    try:
                        resp = await client.get(api_url, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            desc_clean = clean_html_to_text(data.get('content', ''))[:40000]
                            loc_name = data.get('location', {}).get('name', '')
                            if 'bangalore' in loc_name.lower() or 'bengaluru' in loc_name.lower():
                                loc_clean = "Bangalore, India"
                            elif 'hyderabad' in loc_name.lower():
                                loc_clean = "Hyderabad, India"
                            elif loc_name and loc_name.strip() != 'India':
                                loc_clean = loc_name.strip()[:200]
                            else:
                                loc_clean = "Bangalore, India" if 'abnormal' in board_name.lower() else "India"

                            if description_is_valid(desc_clean, title=title):
                                return DetailResult(
                                    description=desc_clean,
                                    location=loc_clean[:200],
                                    employment_type="Full-time",
                                    department="Engineering",
                                    salary_raw="Competitive / Not specified",
                                    source="greenhouse_api",
                                )
                    except Exception:
                        pass

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

        ld_data = extract_job_posting(raw_html_text)

        description = None
        location = None
        employment_type = None

        if ld_data:
            raw_desc = str(ld_data.get("description", ""))
            clean_desc = clean_html_to_text(raw_desc)[:40000]
            if description_is_valid(clean_desc, title=title):
                description = clean_desc

            job_loc = ld_data.get("jobLocation")
            if isinstance(job_loc, list) and job_loc:
                job_loc = job_loc[0]
            if isinstance(job_loc, dict):
                loc_name = job_loc.get("name")
                addr = job_loc.get("address", {})
                if isinstance(addr, dict):
                    loc_city = addr.get("addressLocality") or addr.get("addressRegion") or ""
                    loc_country = addr.get("addressCountry") or ""
                    if loc_country.lower() in ('in', 'ind'):
                        loc_country = "India"
                    elif loc_country.lower() in ('us', 'usa'):
                        loc_country = "United States"
                    location = f"{loc_city}, {loc_country}".strip(" ,") if loc_city else (loc_name or loc_country)
                elif loc_name:
                    location = loc_name

            emp_type = ld_data.get("employmentType")
            if emp_type and str(emp_type).lower() != "other":
                employment_type = str(emp_type).replace("_", "-").capitalize()

        if not location or location.lower() in ('india', 'in', 'pagedata', ''):
            workday_loc_match = re.search(r'/job/([A-Za-z0-9\-%]+)/', apply_url)
            if workday_loc_match:
                raw_city = workday_loc_match.group(1)
                if 'CHENNAI' in raw_city.upper(): location = "Chennai, India"
                elif 'BANGALORE' in raw_city.upper() or 'BENGALURU' in raw_city.upper(): location = "Bangalore, India"
                elif 'HYDERABAD' in raw_city.upper(): location = "Hyderabad, India"
                elif 'NOIDA' in raw_city.upper(): location = "Noida, India"
                elif 'MUMBAI' in raw_city.upper(): location = "Mumbai, India"
                elif 'PUNE' in raw_city.upper(): location = "Pune, India"
                elif 'GURGAON' in raw_city.upper() or 'GURUGRAM' in raw_city.upper(): location = "Gurgaon, India"
                else:
                    c_title = raw_city.replace('-', ' ').title()
                    location = f"{c_title}, India" if not any(x in c_title.lower() for x in ['india', 'usa']) else c_title

            if not location or location.lower() in ('india', 'in', ''):
                gh_loc = re.search(r'<div[^>]*class=["\'][^"\']*location[^"\']*["\'][^>]*>(.*?)</div', raw_html_text, re.DOTALL | re.IGNORECASE)
                if gh_loc:
                    loc_t = re.sub(r'<[^>]+>', ' ', gh_loc.group(1)).strip()
                    if len(loc_t) > 2 and loc_t.lower() != 'india':
                        location = loc_t

            if not location or location.lower() in ('india', 'in', ''):
                city_dom_match = re.search(r'\b(Hyderabad|Bangalore|Bengaluru|Chennai|Noida|Mumbai|Pune|Gurgaon|Gurugram|Delhi)\b', raw_html_text + ' ' + title + ' ' + apply_url, re.IGNORECASE)
                if city_dom_match:
                    city_found = city_dom_match.group(1).capitalize()
                    if city_found == 'Bengaluru': city_found = 'Bangalore'
                    location = f"{city_found}, India"

        if not description:
            desc_match = re.search(r'<(?:div|section)[^>]*class=["\'][^"\']*(?:ats-description|job-description|job-details)[^"\']*["\'][^>]*>(.*?)</(?:div|section)>', raw_html_text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                clean_desc_text = clean_html_to_text(desc_match.group(1))[:40000]
                if description_is_valid(clean_desc_text, title=title):
                    description = clean_desc_text

        if not location or location.lower() == 'india':
            if 'abnormal' in board_name.lower():
                location = "Bangalore, India"
            else:
                location = "India"

        if not employment_type:
            type_match = re.search(r'\b(Full-time|Part-time|Contract|Temporary|Internship)\b', raw_html_text, re.IGNORECASE)
            employment_type = type_match.group(1).capitalize() if type_match else "Full-time"

        dept_match = re.search(r'(?:Department|Team|Function):\s*([A-Za-z0-9\s&]+)', raw_html_text, re.IGNORECASE)
        department = dept_match.group(1).strip() if dept_match else "Engineering"

        salary_raw = None
        salary_min = None
        salary_max = None
        salary_currency = None

        inr_match = re.search(r'(?:INR|₹)\s*([\d,.]+)\s*(?:-|to)\s*(?:INR|₹)?\s*([\d,.]+)', raw_html_text, re.IGNORECASE)
        usd_match = re.search(r'\$\s*([\d,.]+)\s*(?:-|to)\s*\$?\s*([\d,.]+)', raw_html_text)

        if inr_match:
            try:
                c1 = int(inr_match.group(1).replace(',', '').split('.')[0])
                c2 = int(inr_match.group(2).replace(',', '').split('.')[0])
                salary_min = min(c1, c2)
                salary_max = max(c1, c2)
                salary_currency = "INR"
                salary_raw = f"INR {salary_min:,} - INR {salary_max:,} / yr"
            except Exception:
                pass
        elif usd_match:
            try:
                c1 = int(usd_match.group(1).replace(',', '').split('.')[0])
                c2 = int(usd_match.group(2).replace(',', '').split('.')[0])
                salary_min = min(c1, c2)
                salary_max = max(c1, c2)
                salary_currency = "USD"
                salary_raw = f" -  / yr"
            except Exception:
                pass

        if not salary_raw:
            salary_raw = "Competitive / Not specified"

        return {
            "description": description[:40000] if description else None,
            "location": location[:200] if location else None,
            "employment_type": employment_type[:200] if employment_type else None,
            "department": department[:200] if department else None,
            "salary_raw": salary_raw[:200] if salary_raw else None,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency
        }


detail_extractor = DetailExtractor()
