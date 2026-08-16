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
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
    job_keywords = ['/job/', '/jobs/', '/careers/', 'gh_jid=', '/posting/', '/opportunities/', 'jobid=', '/resilinc/', '/weave/', '/aspora/', '/plane/', '/cognite/', '/open-roles/', '/search-jobs/', '/job_details/']

    lever_uuids = re.findall(r'href=["\'](https?://jobs\.lever\.co/[^/]+/[a-f0-9\-]{36})["\']', html)
    hrefs.extend(lever_uuids)
    ashby_uuids = re.findall(r'href=["\'](https?://jobs\.ashbyhq\.com/[^/]+/[a-f0-9\-]{36})["\']', html)
    hrefs.extend(ashby_uuids)

    google_jobs = re.findall(r'href=["\'](\./jobs/results/[a-zA-Z0-9_\-]+)["\']', html)
    hrefs.extend(google_jobs)
    meta_jobs = re.findall(r'href=["\'](/profile/job_details/[0-9]+)["\']', html)
    hrefs.extend(meta_jobs)

    for href in hrefs:
        href_lower = href.lower()
        if any(k in href_lower for k in job_keywords) or re.search(r'[a-f0-9]{8}-[a-f0-9]{4}|job_details', href_lower):
            if href.startswith('/'):
                parsed = urlparse(target_url)
                full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif href.startswith('./'):
                parsed = urlparse(target_url)
                full_url = f"{parsed.scheme}://{parsed.netloc}/about/careers/applications/{href.lstrip('./')}"
            elif href.startswith('http'):
                full_url = href
            else:
                continue

            if full_url in seen_urls or full_url.rstrip('/') == target_url.rstrip('/'):
                continue
            if any(x in full_url.lower() for x in ['search', 'privacy', 'terms', 'login', 'signin', 'cookie', 'gstatic']):
                continue

            seen_urls.add(full_url)

            slug = full_url.rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').capitalize()
            title = slug if len(slug) > 3 else f"Position at {board_name}"

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

                raw_url = f"{target_url.rstrip('/')}/{item.get('externalPath', '').lstrip('/')}"
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

        seen_urls = set()
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', payload)
        parsed_target = urlparse(target_url)

        for href in hrefs:
            href_lower = href.lower()
            if any(k in href_lower for k in ['/job/', '/details/', '/en-us/']) or re.search(r'R-\d+|_R\d+|\bjob\b', href_lower):
                if href.startswith('/'):
                    full_url = f"{parsed_target.scheme}://{parsed_target.netloc}{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if full_url in seen_urls or full_url.rstrip('/') == target_url.rstrip('/'):
                    continue
                if any(x in full_url.lower() for x in ['search', 'privacy', 'terms', 'login', 'signin', 'cookie']):
                    continue

                seen_urls.add(full_url)
                slug = full_url.rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').capitalize()
                title = slug if len(slug) > 3 else f"Position at {board_name}"

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
                        extra_payload={"source_workday_dom": True}
                    )
                )

        return results

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
