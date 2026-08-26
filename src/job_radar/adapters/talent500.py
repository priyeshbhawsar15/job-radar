import json
from typing import List, Dict, Any, Optional
from job_radar.adapters.base import BaseAdapter, ExtractedCandidate
from job_radar.adapters.families import generate_fingerprint


class Talent500Adapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "talent500"

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

        try:
            data = json.loads(payload)
        except Exception:
            return []

        if not isinstance(data, dict):
            return []

        jobs = data.get("data")
        if not isinstance(jobs, list):
            return []

        results: List[ExtractedCandidate] = []
        for item in jobs:
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or item.get("title_alias_1") or "").strip()
            if not title:
                continue

            job_id = str(item.get("id") or "").strip()
            job_code = str(item.get("job_code") or "").strip()
            job_slug = str(item.get("slug") or "").strip()

            if not job_id or not job_slug:
                continue

            company_obj = item.get("company")
            if isinstance(company_obj, dict):
                company_name = (company_obj.get("name") or "").strip() or board_name
                company_slug = (company_obj.get("slug") or "").strip()
            elif isinstance(company_obj, str) and company_obj.strip():
                company_name = company_obj.strip()
                company_slug = ""
            else:
                company_name = board_name
                company_slug = ""

            if not company_slug:
                continue

            raw_url = f"https://talent500.com/jobs/{company_slug}/{job_slug}/"

            city = item.get("location")
            if isinstance(city, str) and city.strip():
                city = city.strip()
            else:
                city = None

            country_obj = item.get("country")
            if isinstance(country_obj, dict):
                country = (country_obj.get("name") or "").strip() or None
            elif isinstance(country_obj, str) and country_obj.strip():
                country = country_obj.strip()
            else:
                country = None

            if city and country:
                if country.lower() in city.lower():
                    location_str: Optional[str] = city
                else:
                    location_str = f"{city}, {country}"
            elif city:
                location_str = city
            elif country:
                location_str = country
            else:
                location_str = None

            if location_filter and location_str:
                if location_filter.lower() not in location_str.lower():
                    continue

            dept = item.get("job_category") or item.get("role_category") or item.get("job_function") or item.get("category")
            if isinstance(dept, dict):
                dept = dept.get("name")
            if dept and str(dept).strip():
                dept = str(dept).strip()
            else:
                dept = None

            emp_type = item.get("employment_type")
            if emp_type and str(emp_type).strip():
                emp_type = str(emp_type).strip()
            else:
                emp_type = None

            desc = item.get("description")

            fp = generate_fingerprint(company_name, title, location_str or "")

            extra_payload: Dict[str, Any] = {
                "talent500_id": job_id,
                "job_code": job_code,
                "slug": job_slug,
                "company_slug": company_slug,
            }
            if desc:
                extra_payload["description"] = desc

            results.append(
                ExtractedCandidate(
                    title=title,
                    company=company_name,
                    location=location_str,
                    department=dept,
                    employment_type=emp_type,
                    raw_url=raw_url,
                    fingerprint=fp,
                    extra_payload=extra_payload
                )
            )

        return results
