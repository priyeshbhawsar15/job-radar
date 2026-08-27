import json
from typing import List, Dict, Any, Optional
from job_radar.adapters.base import BaseAdapter, ExtractedCandidate
from job_radar.adapters.families import generate_fingerprint, extract_html_job_links


class SmartRecruitersAdapter(BaseAdapter):
    @property
    def family(self) -> str:
        return "smartrecruiters"

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
            jobs = data.get("content", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

            for item in jobs:
                title = item.get("name", "").strip()
                if not title:
                    continue

                loc_obj = item.get("location", {})
                if isinstance(loc_obj, dict):
                    city = loc_obj.get("city") or ""
                    country = loc_obj.get("country") or ""
                    location_str = f"{city}, {country}".strip(", ")
                else:
                    location_str = str(loc_obj)

                if country_filter and country_filter.lower() not in location_str.lower():
                    continue
                if location_filter and location_filter.lower() not in location_str.lower():
                    continue

                job_id = item.get("id")
                company = item.get("company") if isinstance(item.get("company"), dict) else {}
                company_identifier = company.get("identifier") if isinstance(company.get("identifier"), str) else None
                raw_url = f"https://jobs.smartrecruiters.com/{company_identifier}/{job_id}" if company_identifier and job_id else target_url

                dept = ""
                dept_obj = item.get("department", {})
                if isinstance(dept_obj, dict):
                    dept = dept_obj.get("label", "")
                elif isinstance(dept_obj, str):
                    dept = dept_obj

                emp_type = ""
                emp_obj = item.get("typeOfEmployment", {})
                if isinstance(emp_obj, dict):
                    emp_type = emp_obj.get("label", "")
                elif isinstance(emp_obj, str):
                    emp_type = emp_obj

                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=board_name,
                        location=location_str or None,
                        department=dept or None,
                        employment_type=emp_type or None,
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"smartrecruiters_id": job_id, "smartrecruiters_company_identifier": company_identifier}
                    )
                )
            if results:
                return results
        except Exception:
            pass

        return extract_html_job_links(payload, board_name, target_url)
