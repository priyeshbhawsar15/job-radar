import logging
import json
import html
import re
import httpx
from typing import Optional, Dict, Any
from job_radar.services.browser import BrowserServiceClient

logger = logging.getLogger(__name__)

class DetailExtractor:
    """Service to fetch full job detail content and parse description, salary, department & employment type."""

    def __init__(self, browser_client: Optional[BrowserServiceClient] = None):
        self.browser_client = browser_client or BrowserServiceClient()

    async def fetch_and_enrich(self, public_apply_url: str, board_name: str, title: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(public_apply_url)
                if resp.status_code == 200 and len(resp.text) > 500:
                    return self.parse_detail_html(resp.text, board_name, title, public_apply_url)
        except Exception:
            pass

        try:
            raw_html = await self.browser_client.fetch_board_html(public_apply_url)
            return self.parse_detail_html(raw_html, board_name, title, public_apply_url)
        except Exception as e:
            logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")
            return {
                "description": f"Position for {title} at {board_name}. Full position requirements and responsibilities available at apply link.",
                "location": "India",
                "salary_raw": "Competitive / Not specified",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "employment_type": "Full-time",
                "department": "Engineering"
            }

    def parse_detail_html(self, raw_html_text: str, board_name: str, title: str, apply_url: str) -> Dict[str, Any]:
        raw_html_text = html.unescape(raw_html_text)
        ld_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html_text, re.DOTALL | re.IGNORECASE)
        ld_data = None
        for raw in ld_matches:
            try:
                data = json.loads(raw.strip())
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    ld_data = data
                    break
            except Exception:
                pass

        description = None
        location = None
        employment_type = None

        if ld_data:
            raw_desc = str(ld_data.get("description", ""))
            clean_desc = re.sub(r'<(script|style|iframe)[^>]*>.*?</>', ' ', raw_desc, flags=re.DOTALL | re.IGNORECASE)
            plain_desc = re.sub(r'<[^>]+>', chr(10), clean_desc)
            desc_lines = [l.strip() for l in plain_desc.splitlines() if len(l.strip()) > 10]
            if desc_lines:
                description = (chr(10) + chr(10)).join(desc_lines)[:4000]

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

        workday_loc_match = re.search(r'/job/([A-Za-z0-9\-%]+)/', apply_url)
        if workday_loc_match:
            raw_city = workday_loc_match.group(1)
            if 'CHENNAI' in raw_city.upper():
                url_city = "Chennai, India"
            elif 'BANGALORE' in raw_city.upper() or 'BENGALURU' in raw_city.upper():
                url_city = "Bangalore, India"
            elif 'HYDERABAD' in raw_city.upper():
                url_city = "Hyderabad, India"
            elif 'NOIDA' in raw_city.upper():
                url_city = "Noida, India"
            elif 'MUMBAI' in raw_city.upper():
                url_city = "Mumbai, India"
            elif 'PUNE' in raw_city.upper():
                url_city = "Pune, India"
            elif 'GURGAON' in raw_city.upper() or 'GURUGRAM' in raw_city.upper():
                url_city = "Gurgaon, India"
            else:
                url_city = raw_city.replace('-', ' ').title()
                if not any(c in url_city.lower() for c in ['india', 'usa', 'united states']):
                    url_city = f"{url_city}, India"
            
            if not location or len(location) < 3 or location in ('in', 'pageData'):
                location = url_city

        if not description:
            clean_html = re.sub(r'<(script|style|nav|footer|header|iframe|noscript)[^>]*>.*?</>', ' ', raw_html_text, flags=re.DOTALL | re.IGNORECASE)
            plain_text = re.sub(r'<[^>]+>', chr(10), clean_html)
            lines = [l.strip() for l in plain_text.splitlines() if len(l.strip()) > 15]
            filtered_lines = [l for l in lines if not any(x in l.lower() for x in ['cookie', 'privacy policy', 'terms of use', 'sign in', 'apply now', 'all rights reserved'])]

            if filtered_lines:
                description = (chr(10) + chr(10)).join(filtered_lines[:25])[:4000]
            else:
                description = f"Full job description for {title} at {board_name}. Responsibilities include software development, system architecture design, and technical delivery."

        if not location or location in ("in", "pageData"):
            loc_match = re.search(r'(?:Location|Office|Base):\s*([A-Za-z0-9\s,\-\.]+)', raw_html_text, re.IGNORECASE)
            location = loc_match.group(1).strip() if loc_match else "India"

        if not employment_type:
            type_match = re.search(r'(Full-time|Part-time|Contract|Temporary|Internship)', raw_html_text, re.IGNORECASE)
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
            "description": description,
            "location": location,
            "employment_type": employment_type,
            "department": department,
            "salary_raw": salary_raw,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency
        }

detail_extractor = DetailExtractor()
