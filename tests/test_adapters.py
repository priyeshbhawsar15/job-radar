import json
import pytest
from job_radar.adapters.registry import adapter_registry
from job_radar.services.browser import validate_target_url, TargetBoundaryViolation

def test_registry_has_default_adapters():
  families = adapter_registry.list_families()
  assert "greenhouse" in families
  assert "lever" in families
  assert "ashby" in families
  assert "workday" in families

def test_greenhouse_adapter_parsing():
  adapter = adapter_registry.get("greenhouse")
  assert adapter is not None

  payload = json.dumps({
    "jobs": [
      {
        "id": 12345,
        "title": "Senior Backend Engineer",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/12345",
        "location": {"name": "San Francisco, CA"},
        "departments": [{"name": "Engineering"}]
      }
    ]
  })

  candidates = adapter.parse_raw_payload(payload, "Stripe", "https://boards.greenhouse.io/stripe")
  assert len(candidates) == 1
  c = candidates[0]
  assert c.title == "Senior Backend Engineer"
  assert c.company == "Stripe"
  assert c.location == "San Francisco, CA"
  assert c.department == "Engineering"
  assert c.fingerprint is not None

def test_oracle_adapter_registration_and_parsing():
    adapter = adapter_registry.get("oracle")
    assert adapter is not None
    assert adapter.__class__.__name__ == "OracleAdapter"

    html_payload = """
    <html>
        <body>
            <a href="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/">Job 337440</a>
        </body>
    </html>
    """
    candidates = adapter.parse_raw_payload(html_payload, "Oracle", "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.title == "Oracle Job Requisition 337440"
    assert c.extra_payload.get("public_job_id") == "337440"


def test_oracle_adapter_html_fallback_builds_vanity_url_without_splitting_jobsearch():
    adapter = adapter_registry.get("oracle")
    assert adapter is not None

    html_payload = """
    <html>
        <body>
            <a href="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/">Job 337440</a>
        </body>
    </html>
    """
    candidates = adapter.parse_raw_payload(
        html_payload,
        "Oracle",
        "https://careers.oracle.com/en/sites/jobsearch/jobs?keyword=Software+Engineer&location=India",
    )
    assert len(candidates) == 1
    assert candidates[0].raw_url == (
        "https://careers.oracle.com/en/sites/jobsearch/job/337440/"
    )


def _load_fixture(name):
    import os
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


def test_oracle_adapter_parses_fusion_requisition_list():
    adapter = adapter_registry.get("oracle")
    assert adapter is not None

    payload = _load_fixture("oracle_requisitions.json")
    candidates = adapter.parse_raw_payload(
        payload,
        "Oracle",
        "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs",
    )

    assert len(candidates) == 2

    by_id = {c.extra_payload.get("public_job_id"): c for c in candidates}
    assert set(by_id.keys()) == {"337440", "337477"}

    c1 = by_id["337440"]
    assert c1.title == "ORACLE_LISTING_TITLE_ONE"
    assert c1.location == "Bengaluru, Karnataka, India"
    assert c1.raw_url == (
        "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/"
    )
    assert c1.extra_payload.get("posted_date") == "2026-08-20T00:00:00+00:00"

    c2 = by_id["337477"]
    assert c2.title == "ORACLE_LISTING_TITLE_TWO"
    assert c2.location == "Hyderabad, Telangana, India"
    assert c2.raw_url == (
        "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337477/"
    )
    assert c2.extra_payload.get("posted_date") == "2026-08-19T00:00:00+00:00"


def test_oracle_adapter_skips_duplicate_or_malformed_fusion_records():
    adapter = adapter_registry.get("oracle")
    assert adapter is not None

    payload = json.dumps({
        "items": [
            {
                "TotalJobsCount": 4,
                "requisitionList": [
                    {
                        "Id": "337440",
                        "Title": "ORACLE_LISTING_TITLE_ONE",
                        "PrimaryLocation": "Bengaluru, Karnataka, India",
                        "PostedDate": "2026-08-20T00:00:00+00:00",
                        "secondaryLocations": []
                    },
                    {
                        "Id": "337440",
                        "Title": "ORACLE_LISTING_TITLE_ONE_DUP",
                        "PrimaryLocation": "Bengaluru, Karnataka, India",
                        "PostedDate": "2026-08-20T00:00:00+00:00",
                        "secondaryLocations": []
                    },
                    {
                        "Id": "not-a-number",
                        "Title": "ORACLE_LISTING_TITLE_BAD_ID",
                        "PrimaryLocation": "Hyderabad, Telangana, India",
                        "PostedDate": "2026-08-19T00:00:00+00:00",
                        "secondaryLocations": []
                    },
                    {
                        "Id": "337500",
                        "Title": "",
                        "PrimaryLocation": "Hyderabad, Telangana, India",
                        "PostedDate": "2026-08-19T00:00:00+00:00",
                        "secondaryLocations": []
                    }
                ]
            }
        ]
    })

    candidates = adapter.parse_raw_payload(
        payload,
        "Oracle",
        "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs",
    )

    assert len(candidates) == 1
    assert candidates[0].extra_payload.get("public_job_id") == "337440"
    assert candidates[0].title == "ORACLE_LISTING_TITLE_ONE"


def test_phenom_adapter_registration_and_parsing():
    adapter = adapter_registry.get("phenom")
    assert adapter is not None
    assert adapter.__class__.__name__ == "PhenomAdapter"

    html_payload = """
    <html>
        <body>
            <a href="https://www.careers.philips.com/in/en/job/501234/Senior-Software-Engineer?utm_source=linkedin#apply">Senior Software Engineer</a>
            <a href="https://www.careers.philips.com/in/en/job/501234/Senior-Software-Engineer">Senior Software Engineer Duplicate</a>
            <a href="https://www.careers.philips.com/in/en/search-results">Search Results</a>
            <a href="https://www.careers.philips.com/in/en/saved-jobs">Saved Jobs</a>
            <a href="https://other-site.com/in/en/job/999999/Offsite-Job">Offsite Job</a>
            <a href="https://www.careers.philips.com/in/en/job/invalid/No-ID">Invalid Job Path</a>
        </body>
    </html>
    """

    candidates = adapter.parse_raw_payload(html_payload, "Philips", "https://www.careers.philips.com/in/en/c/software-development-jobs")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.title == "Senior Software Engineer"
    assert c.company == "Philips"
    assert c.raw_url == "https://www.careers.philips.com/in/en/job/501234/Senior-Software-Engineer"
    assert c.extra_payload.get("requisition_id") == "501234"


def test_target_boundary_validation():
    # Valid host match
    assert validate_target_url(
        "https://boards.greenhouse.io/stripe/jobs/123",
        "https://boards.greenhouse.io/stripe"
    ) is True

    # Mismatched host violation
    with pytest.raises(TargetBoundaryViolation):
        validate_target_url(
            "https://malicious-site.com/jobs",
            "https://boards.greenhouse.io/stripe"
        )

    # Invalid scheme violation
    with pytest.raises(TargetBoundaryViolation):
        validate_target_url("file:///etc/passwd")
