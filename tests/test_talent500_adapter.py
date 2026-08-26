import json
from pathlib import Path
import pytest
from job_radar.adapters.talent500 import Talent500Adapter

FIXTURES_DIR = Path("tests/fixtures/talent500")


def test_talent500_adapter_parse_tmus_payload():
    adapter = Talent500Adapter()
    payload = (FIXTURES_DIR / "tmus.json").read_text()
    board_name = "TMUS"
    target_url = "https://talent500.com/joblist/?company=TMUS+Global+Solutions&sort_by_created_date=1&offset=0&limit=20"

    candidates = adapter.parse_raw_payload(payload, board_name, target_url)

    assert len(candidates) == 20
    first = candidates[0]
    assert first.title == "Manager, Software Engineering"
    assert first.company == "TMUS Global Solutions"
    assert first.location == "Hyderabad, India"
    assert first.raw_url == "https://talent500.com/jobs/t-mobile/manager-software-engineering-hyderabad-T500-28653/"
    assert first.extra_payload.get("talent500_id") == "5c076879-8949-4fa2-a3dd-a6f3a9ba15bc"
    assert first.extra_payload.get("job_code") == "T500-28653"


def test_talent500_adapter_location_formatting():
    adapter = Talent500Adapter()

    # Both city and country
    payload_both = json.dumps({
        "data": [{
            "id": "uuid-1",
            "job_code": "T500-1",
            "slug": "test-slug-1",
            "title": "Engineer",
            "company": {"name": "Test Co", "slug": "test-co"},
            "location": "Bengaluru",
            "country": {"name": "India"}
        }]
    })
    res_both = adapter.parse_raw_payload(payload_both, "Test Co", "https://talent500.com")
    assert res_both[0].location == "Bengaluru, India"

    # City only
    payload_city = json.dumps({
        "data": [{
            "id": "uuid-2",
            "job_code": "T500-2",
            "slug": "test-slug-2",
            "title": "Engineer",
            "company": {"name": "Test Co", "slug": "test-co"},
            "location": "Bengaluru",
            "country": None
        }]
    })
    res_city = adapter.parse_raw_payload(payload_city, "Test Co", "https://talent500.com")
    assert res_city[0].location == "Bengaluru"

    # Country only
    payload_country = json.dumps({
        "data": [{
            "id": "uuid-3",
            "job_code": "T500-3",
            "slug": "test-slug-3",
            "title": "Engineer",
            "company": {"name": "Test Co", "slug": "test-co"},
            "location": None,
            "country": {"name": "India"}
        }]
    })
    res_country = adapter.parse_raw_payload(payload_country, "Test Co", "https://talent500.com")
    assert res_country[0].location == "India"

    # Neither
    payload_none = json.dumps({
        "data": [{
            "id": "uuid-4",
            "job_code": "T500-4",
            "slug": "test-slug-4",
            "title": "Engineer",
            "company": {"name": "Test Co", "slug": "test-co"},
            "location": None,
            "country": None
        }]
    })
    res_none = adapter.parse_raw_payload(payload_none, "Test Co", "https://talent500.com")
    assert res_none[0].location is None


def test_talent500_adapter_rejects_html_fallback():
    adapter = Talent500Adapter()
    html_shell = "<html><body><h1>Jobs Page</h1><a href='/job/123'>Job 1</a></body></html>"

    res = adapter.parse_raw_payload(html_shell, "TMUS", "https://talent500.com")
    assert res == []
