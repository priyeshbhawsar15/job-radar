import html
def canonicalize_job_url(full_url: str, board_name: str, target_url: str) -> str:
    if 'amazon.jobs' in full_url:
        match = re.search(r'/jobs/(\d+)', full_url)
        if match:
            return f'https://www.amazon.jobs/en/jobs/{match.group(1)}'

    if 'eightfold.ai' in full_url or 'eightfold' in board_name.lower():
        match = re.search(r'/job/(\d+)', full_url)
        if match:
            domain_map = {'qualcomm': 'qualcomm.com', 'hp': 'hp.com', 'microsoft': 'microsoft.com'}
            comp_key = board_name.lower()
            domain = domain_map.get(comp_key, f'{comp_key}.com')
            return f'https://{comp_key}.eightfold.ai/careers/job/{match.group(1)}?domain={domain}'

    if 'myworkdayjobs.com' in full_url:
        return full_url

    return full_url.split('?')[0] if '?' in full_url and not any(k in full_url for k in ['gh_jid=', 'jobId=', 'team=']) else full_url

import hashlib
import json
import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from job_radar.adapters.base import BaseAdapter, ExtractedCandidate

def generate_fingerprint(company: str, title: str, location: Optional[str] = None) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def extract_html_job_links(html: str, board_name: str, target_url: str) -> List[ExtractedCandidate]:
    results = []
    seen_urls = set()
    parsed_target = urlparse(target_url)

    job_path_keywords = [
        '/job/', '/jobs/', '/careers/job/', 'gh_jid=', '/posting/', '/opportunities/',
        '/job_details/', '/job-detail/', '/careers-list/', '/open-roles/', 'R-'
    ]

    # Specific Google Careers link pattern matching
    if 'google' in board_name.lower() or 'google.com' in parsed_target.netloc:
        google_matches = re.findall(r'href=["\'](\./jobs/results/[0-9]+[a-zA-Z0-9_\-]+)["\']', html)
        for g_href in google_matches:
            full_url = f"https://www.google.com/about/careers/applications/{g_href.lstrip('./')}"
            if full_url in seen_urls or full_url.rstrip('/') == 'https://www.google.com/about/careers/applications/jobs/results':
                continue
            seen_urls.add(full_url)
            slug = full_url.split('/')[-1]
            title = re.sub(r'^[0-9]+-', '', slug).replace('-', ' ').title()
            fp = generate_fingerprint(board_name, title, "India")
            results.append(
                ExtractedCandidate(
                    title=title,
                    company=board_name,
                    location="India",
                    department=None,
                    employment_type="Full-time",
                    raw_url=full_url,
                    fingerprint=fp,
                    extra_payload={"source_html": True}
                )
            )

    matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)

    for href, inner in matches:
        href_lower = href.lower()
        is_job = any(k in href_lower for k in job_path_keywords) or bool(re.search(r'R-\d+|_R\d+|/job_details/\d+|/details/\d+|/jobs/[0-9a-f\-]{10,}', href_lower))
        if not is_job:
            continue

        if any(x in href_lower for x in ['/privacy', '/terms', '/login', '/signin', '/cookie', 'gstatic', 'facebook.com', 'twitter.com', 'linkedin.com', 'recommendations', 'saved', 'alerts', '.pdf']):
            continue

        if href.startswith('/'):
            full_url = f"{parsed_target.scheme}://{parsed_target.netloc}{href}"
        elif href.startswith('./'):
            full_url = f"{parsed_target.scheme}://{parsed_target.netloc}/about/careers/applications/{href.lstrip('./')}"
        elif href.startswith('http'):
            full_url = href
        else:
            continue

        if 'myworkdayjobs.com' in full_url:
            clean_url = full_url
        else:
            clean_url = canonicalize_job_url(full_url, board_name, target_url)

        if clean_url in seen_urls or clean_url.rstrip('/') == target_url.rstrip('/'):
            continue
        if clean_url.rstrip('/') == 'https://www.google.com/about/careers/applications/jobs/results':
            continue

        seen_urls.add(clean_url)

        clean_text = re.sub(r'<[^>]+>', ' ', inner).strip()
        clean_text = ' '.join(clean_text.split())

        if 'highradius' in board_name.lower() or 'gh_jid=' in clean_url:
            match_hr = re.search(r'(?:[A-Z][a-z]+\s+\d{4}|United States|India|State)\s+([A-Za-z0-9\s\-\/\,]+?)(?:<h3|&lt;h3| Summary | Job Description |$)', clean_text)
            if match_hr and len(match_hr.group(1).strip()) > 3:
                title = match_hr.group(1).strip()
            else:
                title = clean_text.split('Summary')[0].strip()
        elif clean_text and len(clean_text) > 3 and not any(x in clean_text.lower() for x in ['apply', 'view', 'read more', 'learn more', 'details', 'work_outline', 'results']):
            title = clean_text.split(' \b ')[0].split(' Bangalore')[0].split(' India')[0].split(' Engineering Hybrid')[0].split(' Hybrid -')[0].rstrip(' →').strip()
            title = title.split(' ⋅ ')[0]  # Handle clean splitting if dot character is present
        else:
            slug = clean_url.rstrip('/').split('/')[-1]
            slug_clean = re.sub(r'^[0-9a-f\-]+[-_]', '', slug).replace('-', ' ').replace('_', ' ').title()
            title = slug_clean if len(slug_clean) > 3 else f"Position at {board_name}"

        fp = generate_fingerprint(board_name, title, "India")
        results.append(
            ExtractedCandidate(
                title=title,
                company=board_name,
                location="India",
                department=None,
                employment_type="Full-time",
                raw_url=clean_url,
                fingerprint=fp,
                extra_payload={"source_html": True}
            )
        )

    return results

class GreenhouseAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "greenhouse"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')

        country_filter = (selector_config or {}).get("country")
        location_filter = (selector_config or {}).get("location")

        results: List[ExtractedCandidate] = []
        try:
            data = json.loads(payload)
            jobs = data.get("jobs", []) if isinstance(data, dict) else data
            for item in jobs:
                title = item.get("title", "").strip()
                if not title:
                    continue
                location_obj = item.get("location", {})
                location_str = location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj or "")

                if country_filter and country_filter.lower() not in location_str.lower():
                    continue
                if location_filter and location_filter.lower() not in location_str.lower():
                    continue

                raw_url = item.get("absolute_url") or f"{target_url}#job-{item.get('id')}"
                dept = ""
                departments = item.get("departments", [])
                if departments and isinstance(departments, list):
                    dept = departments[0].get("name", "")

                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location=location_str or None,
                        department=dept or None,
                        employment_type=item.get("metadata", {}).get("employment_type"),
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"greenhouse_id": item.get("id")}
                    )
                )
        except Exception:
            return extract_html_job_links(payload, board_name, target_url)

        return results

class LeverAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "lever"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')

        country_filter = (selector_config or {}).get("country")
        location_filter = (selector_config or {}).get("location")

        results: List[ExtractedCandidate] = []
        try:
            data = json.loads(payload)
            if isinstance(data, list):
                jobs = data
            else:
                jobs = data.get("postings", [])

            for item in jobs:
                title = item.get("text", "").strip()
                if not title:
                    continue
                categories = item.get("categories", {})
                location_str = categories.get("location", "")
                dept = categories.get("department", "")
                employment = categories.get("commitment", "")
                raw_url = item.get("hostedUrl") or item.get("applyUrl") or target_url
                item_country = item.get("country") or categories.get("country")

                if country_filter:
                    match_country = item_country and (item_country.upper() == country_filter.upper())
                    match_loc = location_str and (country_filter.lower() in location_str.lower())
                    if not (match_country or match_loc):
                        continue

                if location_filter and location_filter.lower() not in (location_str or "").lower():
                    continue

                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location=location_str or None,
                        department=dept or None,
                        employment_type=employment or None,
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"lever_id": item.get("id"), "country": item_country}
                    )
                )
        except Exception:
            return extract_html_job_links(payload, board_name, target_url)

        return results

class AshbyAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "ashby"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')

        location_filter = (selector_config or {}).get("location")

        results: List[ExtractedCandidate] = []
        try:
            data = json.loads(payload)
            jobs = data.get("jobs", []) if isinstance(data, dict) else data

            for item in jobs:
                title = item.get("title", "").strip()
                if not title:
                    continue
                location_str = item.get("location", "")

                if location_filter and location_filter.lower() not in (location_str or "").lower():
                    continue

                dept = item.get("department", "")
                employment = item.get("employmentType", "")
                raw_url = item.get("jobUrl") or f"{target_url}#job-{item.get('id')}"

                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location=location_str or None,
                        department=dept or None,
                        employment_type=employment or None,
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"ashby_id": item.get("id")}
                    )
                )
        except Exception:
            return extract_html_job_links(payload, board_name, target_url)

        return results

class WorkdayAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "workday"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')

        location_filter = (selector_config or {}).get("location")
        results: List[ExtractedCandidate] = []

        try:
            data = json.loads(payload)
            postings = data.get("jobPostings", [])
            for item in postings:
                title = item.get("title", "").strip()
                if not title:
                    continue
                location_str = item.get("locationsText", "")

                if location_filter and location_filter.lower() not in (location_str or "").lower():
                    continue

                base_target = target_url.split('?')[0].rstrip('/')
                raw_url = f"{base_target}/{item.get('externalPath', '').lstrip('/')}"
                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location=location_str or None,
                        department=None,
                        employment_type=item.get("timeType"),
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"bulletFields": item.get("bulletFields", [])}
                    )
                )
            if results:
                return results
        except Exception:
            pass

        return extract_html_job_links(payload, board_name, target_url)

class GenericAdapter(BaseAdapter):
    def __init__(self, family_name: str):
        self._family_name = family_name

    @property
    def family(self) -> str:
        return self._family_name

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        try:
            data = json.loads(payload)
            if isinstance(data, dict) and "jobs" in data:
                return extract_html_job_links(json.dumps(data), board_name, target_url)
        except Exception:
            pass
        return extract_html_job_links(payload, board_name, target_url)

class AmeripriseAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "ameriprise"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        results: List[ExtractedCandidate] = []
        seen = set()

        parts = payload.split("/search-jobs/")
        for part in parts[1:]:
            sub = part.split('"')[0].split("'")[0].split(">")[0].strip()
            sub_parts = [p for p in sub.split("/") if p]
            if len(sub_parts) >= 2 and sub_parts[0].startswith("r"):
                job_id = sub_parts[0]
                slug = sub_parts[1]
                path = f"/search-jobs/{job_id}/{slug}/"
                full_url = f"https://careers.ameriprise.com{path}"
                clean_url = canonicalize_job_url(full_url, board_name, target_url)
                if clean_url in seen:
                    continue
                seen.add(clean_url)

                title = slug.replace("-", " ").title()
                fp = generate_fingerprint(board_name, f"{title} {job_id}", "India")
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location="India",
                        department="Technology",
                        employment_type="Full-time",
                        raw_url=clean_url,
                        fingerprint=fp
                    )
                )

        return results

class OracleAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "oracle"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        results: List[ExtractedCandidate] = []
        seen = set()

        # Parse links containing /job/<number>/ from HTML
        parts = html_text.split("/job/")
        for part in parts[1:]:
            job_id_str = part.split("/")[0].split("?")[0].split('"')[0].split("'")[0].strip()
            if job_id_str.isdigit():
                full_url = target_url.split("/jobs")[0] + f"/job/{job_id_str}/"
                clean_url = canonicalize_job_url(full_url, board_name, target_url)
                if not clean_url or clean_url in seen:
                    continue
                seen.add(clean_url)

                title = f"{board_name} Job Requisition {job_id_str}"
                fp = generate_fingerprint(board_name, f"{title} {job_id_str}", "India")
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location="India",
                        department="Technology",
                        employment_type="Full-time",
                        raw_url=clean_url,
                        fingerprint=fp,
                        extra_payload={"public_job_id": job_id_str}
                    )
                )

        return results


class PhenomAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "phenom"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        results: List[ExtractedCandidate] = []
        seen = set()
        parsed_target = urlparse(target_url)

        matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.DOTALL | re.IGNORECASE)

        for href, inner in matches:
            href_clean = href.strip()
            if href_clean.startswith("/"):
                full_url = f"https://{parsed_target.netloc}{href_clean}"
            elif href_clean.startswith("http"):
                full_url = href_clean
            else:
                continue

            parsed_url = urlparse(full_url)
            if parsed_url.scheme != "https" or parsed_url.netloc != parsed_target.netloc:
                continue

            path_match = re.search(r'/job/(\d+)/([^/?#]+)', parsed_url.path)
            if not path_match:
                continue

            req_id = path_match.group(1)
            slug = path_match.group(2)
            if not req_id or not slug:
                continue

            clean_url = f"https://{parsed_url.netloc}{parsed_url.path}"
            if clean_url in seen:
                continue
            seen.add(clean_url)

            clean_text = re.sub(r'<[^>]+>', ' ', inner).strip()
            clean_text = ' '.join(clean_text.split())
            if not clean_text or clean_text.lower() in ('apply', 'apply now', 'read more', 'saved jobs', 'search results'):
                clean_text = slug.replace('-', ' ').title()

            fp = generate_fingerprint(board_name, clean_text, "India")
            results.append(
                ExtractedCandidate(
                    title=clean_text,
                    company=board_name,
                    location="India",
                    department="Engineering",
                    employment_type="Full-time",
                    raw_url=clean_url,
                    fingerprint=fp,
                    extra_payload={"requisition_id": req_id}
                )
            )

        return results

class AvatureAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "avature"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        results: List[ExtractedCandidate] = []
        seen = set()

        # Parse links containing /JobDetail/ in HTML
        parts = html_text.split("/JobDetail")
        for part in parts[1:]:
            sub = part.split('"')[0].split("'")[0].split(">")[0].strip()
            # E.g., /Principal-Software-Development-Engineer/141645 or ?jobId=141645
            if sub.startswith("/"):
                sub_parts = [p for p in sub.split("/") if p]
                if len(sub_parts) >= 2:
                    slug = sub_parts[0]
                    job_id = sub_parts[1]
                    raw_u = f"https://careers.tesco.com/en_GB/careers/JobDetail/{slug}/{job_id}"
                    clean_url = canonicalize_job_url(raw_u, board_name, target_url)
                    if not clean_url or clean_url in seen:
                        continue
                    seen.add(clean_url)

                    title = slug.replace("-", " ").title()
                    fp = generate_fingerprint(board_name, f"{title} {job_id}", "Bengaluru, India")
                    results.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location="Bengaluru, India",
                            department="Technology",
                            employment_type="Full-time",
                            raw_url=clean_url,
                            fingerprint=fp
                        )
                    )

        return results

class EightfoldAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "eightfold"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        parsed_target = urllib.parse.urlparse(target_url)
        base_domain = f"https://{parsed_target.netloc}"

        # 1. Parse JSON-LD if present (e.g. Microsoft / HP / Qualcomm single job or page)
        json_ld_desc = ""
        m_ld = re.search(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.DOTALL)
        if m_ld:
            try:
                ld_data = json.loads(m_ld.group(1).strip())
                if isinstance(ld_data, dict) and ld_data.get("@type") == "JobPosting":
                    json_ld_desc = html.unescape(re.sub(r'<[^>]+>', ' ', ld_data.get("description", ""))).strip()
            except Exception:
                pass

        # 2. Parse job links
        parts = html_text.split("/job/")
        results: List[ExtractedCandidate] = []
        seen = set()

        for part in parts[1:]:
            job_id_str = part.split("/")[0].split("?")[0].split('"')[0].split("'")[0].split("#")[0].strip()
            if job_id_str.isdigit():
                full_url = f"{base_domain}/careers/job/{job_id_str}"
                clean_url = canonicalize_job_url(full_url, board_name, target_url)
                if not clean_url or clean_url in seen:
                    continue
                seen.add(clean_url)

                title = f"{board_name} Job Requisition {job_id_str}"

                # Extract title from nearby text if available
                title_match = re.search(r'>([^<]{3,100})</a>', part[:200])
                if title_match:
                    t_cand = title_match.group(1).strip()
                    if len(t_cand) > 3 and not t_cand.startswith("http"):
                        title = t_cand

                fp = generate_fingerprint(board_name, f"{title} {job_id_str}", "India")

                extra = {}
                if json_ld_desc:
                    extra = {"description": json_ld_desc[:40000]}

                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location="India",
                        department="Engineering",
                        employment_type="Full-time",
                        raw_url=clean_url,
                        fingerprint=fp,
                        extra_payload=extra
                    )
                )

        return results

class GoogleCareersAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "google_careers"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        results: List[ExtractedCandidate] = []
        seen = set()

        parts = html_text.split("jobs/results/")
        for part in parts[1:]:
            sub = part.split('"')[0].split("'")[0].split(">")[0].split("?")[0].strip()
            sub_parts = [p for p in sub.split("/") if p]
            if sub_parts and "-" in sub_parts[0]:
                raw_slug = sub_parts[0]
                slug_bits = raw_slug.split("-")
                job_id = slug_bits[0]
                if job_id.isdigit():
                    title_slug = "-".join(slug_bits[1:])
                    full_u = f"https://www.google.com/about/careers/applications/jobs/results/{job_id}-{title_slug}"
                    clean_url = canonicalize_job_url(full_u, board_name, target_url)
                    if not clean_url or clean_url in seen:
                        continue
                    seen.add(clean_url)

                    title = title_slug.replace("-", " ").title()
                    fp = generate_fingerprint(board_name, f"{title} {job_id}", "India")
                    results.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location="India",
                            department="Engineering",
                            employment_type="Full-time",
                            raw_url=clean_url,
                            fingerprint=fp
                        )
                    )

        return results

class MetaCareersAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "meta_careers"

    def parse_raw_payload(
        self,
        payload: str | bytes,
        board_name: str,
        target_url: str,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        html_text = html.unescape(payload)
        results: List[ExtractedCandidate] = []
        seen = set()

        # Parse links containing /job_details/ or /jobs/results/ in HTML
        parts = html_text.split("/job_details/")
        if len(parts) <= 1:
            parts = html_text.split("/jobs/results/")

        for part in parts[1:]:
            sub = part.split('"')[0].split("'")[0].split(">")[0].split("?")[0].strip()
            job_id_str = sub.split("-")[0].strip()
            if job_id_str.isdigit():
                full_u = f"https://www.metacareers.com/profile/job_details/{job_id_str}"
                clean_url = canonicalize_job_url(full_u, board_name, target_url)
                if not clean_url or clean_url in seen:
                    continue
                seen.add(clean_url)

                title = f"{board_name} Job Requisition {job_id_str}"
                fp = generate_fingerprint(board_name, f"{title} {job_id_str}", "India")
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location="India",
                        department="Engineering",
                        employment_type="Full-time",
                        raw_url=clean_url,
                        fingerprint=fp
                    )
                )

        return results
