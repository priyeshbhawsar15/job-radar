import json
from typing import List, Dict, Any, Optional
from job_radar.adapters.base import BaseAdapter, ExtractedCandidate
from job_radar.adapters.families import generate_fingerprint, extract_html_job_links


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

        results: List[ExtractedCandidate] = []
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                jobs = data.get("results") or data.get("data") or data.get("jobs", [])
            elif isinstance(data, list):
                jobs = data
            else:
                jobs = []

            for item in jobs:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or item.get("job_title") or "").strip()
                if not title:
                    continue

                location_str = item.get("location") or "India"
                if location_filter and location_filter.lower() not in (location_str or "").lower():
                    continue

                job_id = str(item.get("id") or item.get("job_id") or "")
                raw_url = item.get("url") or item.get("link") or f"{target_url}#job-{job_id}"
                dept = item.get("department") or item.get("category") or "Engineering"
                emp_type = item.get("employment_type") or "Full-time"
                desc = item.get("description")

                fp = generate_fingerprint(board_name, title, location_str)
                results.append(
                    ExtractedCandidate(
                        title=title,
                        company=item.get("company") or board_name,
                        location=location_str,
                        department=dept,
                        employment_type=emp_type,
                        raw_url=raw_url,
                        fingerprint=fp,
                        extra_payload={"talent500_id": job_id, "description": desc} if desc else {"talent500_id": job_id}
                    )
                )
            if results:
                return results
        except Exception:
            pass

        return extract_html_job_links(payload, board_name, target_url)
