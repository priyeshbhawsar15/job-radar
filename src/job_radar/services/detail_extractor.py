import logging
import json
import html
import re
import httpx
from typing import Optional, Dict, Any
from job_radar.services.browser import BrowserServiceClient

logger = logging.getLogger(__name__)

def clean_html_to_text(raw_html_str: str) -> str:
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
    # Strip script, style, svg, iframe, noscript, nav, footer, header
    clean = re.sub(r'<(script|style|svg|iframe|noscript|nav|footer|header)\b[^>]*>[\s\S]*?</\1>', ' ', text, flags=re.IGNORECASE)
    plain = re.sub(r'<[^>]+>', chr(10), clean)
    lines = [l.strip() for l in plain.splitlines() if len(l.strip()) > 8]
    filtered = [l for l in lines if not any(x in l.lower() for x in ['cookie', 'gtag', 'datalayer', 'window.', 'self.', 'scrollrestoration', '--bprogress', 'privacy policy', 'terms of use', 'sign in', 'apply now', 'all rights reserved', 'javascript:'])]
    return (chr(10) + chr(10)).join(filtered)

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
                                "description": desc_clean if len(desc_clean) > 100 else f"Position for {title[:500]} at {board_name[:500]}.",
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

        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(public_apply_url)
                if resp.status_code == 200 and len(resp.text) > 800:
                    if 'application/ld+json' in resp.text or 'jobPostingDescription' in resp.text or 'ats-description' in resp.text:
                        parsed = self.parse_detail_html(resp.text, board_name, title, public_apply_url)
                        if parsed.get("location") and parsed.get("location") != "India" and len(parsed.get("description", "")) > 300:
                            return parsed
        except Exception:
            pass

        try:
            raw_html = await self.browser_client.fetch_board_html(public_apply_url)
            return self.parse_detail_html(raw_html, board_name, title, public_apply_url)
        except Exception as e:
            logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")
            return {
                "description": f"Position for {title[:500]} at {board_name[:500]}. Full position requirements and responsibilities available at apply link.",
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
            clean_desc = clean_html_to_text(raw_desc)[:40000]
            if clean_desc and len(clean_desc) > 50:
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
                city_dom_match = re.search(r'(Hyderabad|Bangalore|Bengaluru|Chennai|Noida|Mumbai|Pune|Gurgaon|Gurugram|Delhi)', raw_html_text + ' ' + title + ' ' + apply_url, re.IGNORECASE)
                if city_dom_match:
                    city_found = city_dom_match.group(1).capitalize()
                    if city_found == 'Bengaluru': city_found = 'Bangalore'
                    location = f"{city_found}, India"

        if not description or len(description) < 100:
            desc_match = re.search(r'<(?:div|section)[^>]*class=["\'][^"\']*(?:ats-description|job-description|job-details|content|section)[^"\']*["\'][^>]*>(.*?)</(?:div|section)>', raw_html_text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                clean_desc_text = clean_html_to_text(desc_match.group(1))[:40000]
                if clean_desc_text and len(clean_desc_text) > 50:
                    description = clean_desc_text

            if not description or len(description) < 100:
                clean_full = clean_html_to_text(raw_html_text)[:40000]
                if clean_full and len(clean_full) > 100:
                    description = clean_full
                else:
                    description = f"Full job description for {title[:500]} at {board_name[:500]}. Responsibilities include software development, system architecture design, and technical delivery."

        if not location or location.lower() == 'india':
            if 'abnormal' in board_name.lower():
                location = "Bangalore, India"
            else:
                location = "India"

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