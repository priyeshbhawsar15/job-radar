import logging
import json
import html
import re
import httpx
from typing import Optional, Dict, Any, Iterator, List
from job_radar.services.browser import BrowserServiceClient

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


def extract_oracle_description(record: Dict[str, Any], requisition_id: str) -> Optional[str]:
    if not isinstance(record, dict):
        return None

    items = record.get("items")
    if not isinstance(items, list):
        return None

    target_item = None
    req_str = str(requisition_id).strip()
    for item in items:
        if isinstance(item, dict):
            item_req_id = str(item.get("RequisitionId") or item.get("requisitionId") or "").strip()
            if item_req_id == req_str:
                target_item = item
                break

    if not target_item:
        return None

    raw_desc = target_item.get("Description") or target_item.get("description")
    if not raw_desc:
        return None

    cleaned = clean_html_to_text(str(raw_desc))[:40000]
    if description_is_valid(cleaned):
        return cleaned

    return None


def extract_phenom_description(raw_html: str, title: str = "") -> Optional[str]:
    if not raw_html or not isinstance(raw_html, str):
        return None

    posting = extract_job_posting(raw_html)
    if posting:
        raw_desc = str(posting.get("description", ""))
        cleaned = clean_html_to_text(raw_desc)[:40000]
        if description_is_valid(cleaned, title=title):
            return cleaned

    desc_match = re.search(
        r'<(?:div|section|article)[^>]*class=["\'][^"\']*(?:ats-description|job-description|job-details|ph-caption|description)[^"\']*["\'][^>]*>(.*?)</(?:div|section|article)>',
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if desc_match:
        cleaned = clean_html_to_text(desc_match.group(1))[:40000]
        if description_is_valid(cleaned, title=title):
            return cleaned

    cleaned_full = clean_html_to_text(raw_html)[:40000]
    if description_is_valid(cleaned_full, title=title):
        return cleaned_full

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

    return has_boundaries and indicator_count >= 2


def clean_html_to_text(raw_html_str: str) -> str:
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
    # Strip script, style, svg, iframe, noscript, nav, footer, header
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


class DetailExtractor:
    """Service to fetch full job detail content and parse description, salary, department & employment type."""

    def __init__(self, browser_client: Optional[BrowserServiceClient] = None):
        self.browser_client = browser_client or BrowserServiceClient()

    async def fetch_and_enrich(self, public_apply_url: str, board_name: str, title: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        # Direct Greenhouse Public API for Greenhouse boards / gh_jid URLs
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
                    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers) as client:
                        resp = await client.get(api_url)
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

                            return {
                                "description": desc_clean if description_is_valid(desc_clean, title=title) else None,
                                "location": loc_clean[:200],
                                "employment_type": "Full-time",
                                "department": "Engineering",
                                "salary_raw": "Competitive / Not specified",
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None
                            }
                except Exception:
                    pass

        # Oracle Candidate Experience path
        oracle_match = re.search(r'/job/(\d+)', public_apply_url)
        if oracle_match:
            req_id = oracle_match.group(1)
            try:
                record = await self.browser_client.fetch_oracle_detail_record(public_apply_url)
                if record:
                    oracle_desc = extract_oracle_description(record, req_id)
                    if oracle_desc:
                        loc = None
                        items = record.get("items", [])
                        if items and isinstance(items[0], dict):
                            loc = items[0].get("PrimaryLocation") or items[0].get("primaryLocation")
                        return {
                            "description": oracle_desc[:40000],
                            "location": loc[:200] if loc else "India",
                            "employment_type": "Full-time",
                            "department": "Engineering",
                            "salary_raw": "Competitive / Not specified",
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None
                        }
            except Exception as e:
                logger.info(f"Oracle record enrichment failed for {public_apply_url}: {e}")

            return {
                "description": None,
                "location": "India",
                "salary_raw": "Competitive / Not specified",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "employment_type": "Full-time",
                "department": "Engineering"
            }

        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(public_apply_url)
                if resp.status_code == 200 and len(resp.text) > 800:
                    parsed = self.parse_detail_html(resp.text, board_name, title, public_apply_url)
                    if parsed.get("description") or parsed.get("location"):
                        return parsed
        except Exception:
            pass

        try:
            raw_html = await self.browser_client.fetch_board_html(public_apply_url)
            return self.parse_detail_html(raw_html, board_name, title, public_apply_url)
        except Exception as e:
            logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")
            return {
                "description": None,
                "location": "Bangalore, India" if 'abnormal' in board_name.lower() else "India",
                "salary_raw": "Competitive / Not specified",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "employment_type": "Full-time",
                "department": "Engineering"
            }

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
