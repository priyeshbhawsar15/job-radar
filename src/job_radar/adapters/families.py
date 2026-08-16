import hashlib
import json
from typing import List, Dict, Any, Optional
from job_radar.adapters.base import BaseAdapter, ExtractedCandidate

def generate_fingerprint(company: str, title: str, location: Optional[str] = None) -> str:
  """Generate deterministic sha256 fingerprint for deduplication."""
  raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
  return hashlib.sha256(raw.encode('utf-8')).hexdigest()

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

    results: List[ExtractedCandidate] = []
    try:
      data = json.loads(payload)
      jobs = data.get("jobs", [])
      for item in jobs:
        title = item.get("title", "").strip()
        if not title:
          continue
        location_obj = item.get("location", {})
        location_str = location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj or "")
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
    except Exception as e:
      raise ValueError(f"Greenhouse json parse failure: {str(e)}")

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
            extra_payload={"lever_id": item.get("id")}
          )
        )
    except Exception as e:
      raise ValueError(f"Lever json parse failure: {str(e)}")

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

    results: List[ExtractedCandidate] = []
    try:
      data = json.loads(payload)
      jobs = data.get("jobs", []) if isinstance(data, dict) else data

      for item in jobs:
        title = item.get("title", "").strip()
        if not title:
          continue
        location_str = item.get("location", "")
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
    except Exception as e:
      raise ValueError(f"Ashby json parse failure: {str(e)}")

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

    results: List[ExtractedCandidate] = []
    try:
      data = json.loads(payload)
      postings = data.get("jobPostings", [])
      for item in postings:
        title = item.get("title", "").strip()
        if not title:
          continue
        location_str = item.get("locationsText", "")
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
    except Exception as e:
      raise ValueError(f"Workday json parse failure: {str(e)}")

    return results
