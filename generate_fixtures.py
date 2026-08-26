"""Generate static test fixtures for all 65 target boards from canary evidence."""

import json
from pathlib import Path

FIXTURES_DIR = Path("tests/fixtures")

NAME_MAP = {
    "phonepay": "phonepe",
    "hobspot": "hubspot",
    "godaddy": "godaddy",
    "workday": "workdaycorp",
    "publicis_sapient": "publicissapient",
}

def create_fixtures():
    with open("canary_results.json") as f:
        canary = json.load(f)

    for item in canary:
        num = item["num"]
        raw_name = item["name"].lower().replace(" ", "_").replace(".", "").replace("-", "_")
        name_clean = NAME_MAP.get(raw_name, raw_name)
        name = item["name"]
        family = item["family"]
        sample = item.get("raw_payload_sample") or {}
        
        target_dir = FIXTURES_DIR / family
        target_dir.mkdir(parents=True, exist_ok=True)
        fixture_path = target_dir / f"{name_clean}.json"

        loc = item.get("sample_location") or "Bengaluru, India"
        if "india" not in loc.lower():
            loc = f"{loc}, India"

        if family == "greenhouse":
            payload_data = {
                "jobs": [
                    {
                        "id": sample.get("id") or 1001,
                        "title": sample.get("title") or f"Software Engineer - {name}",
                        "absolute_url": item["sample_url"] or f"https://job-boards.greenhouse.io/{name_clean}/jobs/1001",
                        "location": {"name": loc},
                        "departments": [{"name": "Engineering"}]
                    }
                ]
            }
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "ashby":
            payload_data = {
                "jobs": [
                    {
                        "id": sample.get("id") or "ashby_1001",
                        "title": sample.get("title") or f"Backend Engineer - {name}",
                        "jobUrl": item["sample_url"] or f"https://jobs.ashbyhq.com/{name_clean}/ashby_1001",
                        "location": loc,
                        "department": "Engineering",
                        "employmentType": "FullTime"
                    }
                ]
            }
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "lever":
            payload_data = [
                {
                    "id": sample.get("id") or "lever_1001",
                    "text": sample.get("title") or f"Senior Software Engineer - {name}",
                    "hostedUrl": item["sample_url"] or f"https://jobs.lever.co/{name_clean}/lever_1001",
                    "categories": {
                        "location": loc,
                        "department": "Engineering",
                        "commitment": "Full-time"
                    }
                }
            ]
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "workday":
            payload_data = {
                "total": 1,
                "jobPostings": [
                    {
                        "title": sample.get("title") or f"Software Development Engineer - {name}",
                        "externalPath": "/job/R-1001",
                        "locationsText": loc,
                        "timeType": "Full time",
                        "bulletFields": ["R-1001"]
                    }
                ]
            }
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "smartrecruiters":
            payload_data = {
                "content": [
                    {
                        "id": sample.get("id") or "sr_1001",
                        "name": sample.get("name") or f"Lead Engineer - {name}",
                        "location": {"city": "Bangalore", "country": "in"},
                        "department": {"label": "Engineering"},
                        "typeOfEmployment": {"label": "Full-time"}
                    }
                ]
            }
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "talent500":
            payload_data = {
                "results": [
                    {
                        "id": "t500_1001",
                        "title": f"Senior Full Stack Developer - {name}",
                        "url": item["sample_url"] or item["target_url"],
                        "location": loc,
                        "department": "Engineering"
                    }
                ]
            }
            fixture_path.write_text(json.dumps(payload_data, indent=2))

        elif family == "eightfold":
            sample_u = f"https://{name_clean}.eightfold.ai/careers/job/8001"
            sample_t = f"Software Engineer II - {name}"
            html_content = f'<html><body><script type="application/ld+json">{{"@type":"JobPosting","title":"{sample_t}","description":"Job description for {name}"}}</script><a href="{sample_u}">{sample_t}</a></body></html>'
            fixture_path.write_text(html_content)

        elif family == "phenom":
            sample_u = f"https://careers.{name_clean}.com/job/9001/software-engineer"
            sample_t = f"Staff Software Engineer - {name}"
            html_content = f'<html><body><div class="job-item"><a href="{sample_u}">{sample_t}</a></div></body></html>'
            fixture_path.write_text(html_content)

        elif family == "zoho":
            html_content = f'<html><body><a href="https://www.zoho.com/careers/job/1001">Software Engineer - {name}</a></body></html>'
            fixture_path.write_text(html_content)

        else: # custom
            sample_u = f"https://careers.{name_clean}.com/job/1001/software-engineer"
            sample_t = f"Engineering Role - {name}"
            html_content = f'<html><body><a href="{sample_u}">{sample_t}</a></body></html>'
            fixture_path.write_text(html_content)

    print(f"Generated static test fixtures for 65 boards in {FIXTURES_DIR}")

if __name__ == "__main__":
    create_fixtures()
