from pathlib import Path

from job_radar.services.detail_contracts import ERR_DESCRIPTION_MISSING, ERR_DESCRIPTION_INVALID
from job_radar.services.zoho_detail import (
    clean_zoho_description_html,
    extract_zoho_summary_fields,
    extract_zoho_city,
    extract_zoho_date_opened,
    fetch_zoho_detail_from_html,
)

FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


def _load_fixture() -> str:
    return (FIXTURES / "zoho_detail.html").read_text()


def test_extract_zoho_summary_fields_parses_city_and_date_opened():
    raw = _load_fixture()
    fields = extract_zoho_summary_fields(raw)
    assert fields["City"] == "Pune City"
    assert fields["Date Opened"] == "09/02/2025"
    assert fields["Job Type"] == "Full time"


def test_extract_zoho_city_and_date_opened_helpers():
    fields = {"City": "Pune City", "Date Opened": "09/02/2025"}
    assert extract_zoho_city(fields) == "Pune City"
    assert extract_zoho_date_opened(fields) == "09/02/2025"


def test_extract_zoho_city_missing_returns_none():
    assert extract_zoho_city({}) is None
    assert extract_zoho_date_opened({}) is None


def test_clean_zoho_description_html_strips_script_and_style_and_cdn_path():
    raw = (
        "<script>var cdnPathForStaticFiles = \"https://static.zohocdn.com/recruit\";</script>"
        "<style>.leaked { color: red; }</style>"
        "<h3>About the Role</h3>"
        "<p>ZOHO_TOKEN Build things with FastAPI and React and PostgreSQL databases every single day.</p>"
        "<ul><li>Design APIs.</li><li>Ship features.</li></ul>"
    )
    cleaned = clean_zoho_description_html(raw)
    assert "cdnPathForStaticFiles" not in cleaned
    assert "leaked" not in cleaned
    assert "<script>" not in cleaned and "<style>" not in cleaned
    assert "ZOHO_TOKEN" in cleaned
    assert "• Design APIs." in cleaned
    assert "• Ship features." in cleaned
    assert "<p>" not in cleaned and "<li>" not in cleaned


def test_clean_zoho_description_html_empty_input():
    assert clean_zoho_description_html("") == ""
    assert clean_zoho_description_html(None) == ""


def test_fetch_zoho_detail_from_html_success():
    raw = _load_fixture()
    result = fetch_zoho_detail_from_html(raw, "https://wynploy.zohorecruit.in/jobs/Careers/1/Front-End-Developer")

    assert result.error_code is None
    assert result.source == "zoho_rendered_detail"
    assert result.location == "Pune City"
    assert "ZOHO_DETAIL_FIXTURE_FULL_DESCRIPTION_TOKEN" in result.description
    assert "cdnPathForStaticFiles" not in result.description
    assert "hydration marker leaked" not in result.description
    assert "leaked" not in result.description
    assert "<script>" not in result.description and "<style>" not in result.description
    assert "• Design and implement" in result.description
    assert "<p>" not in result.description and "<li>" not in result.description


def test_fetch_zoho_detail_from_html_missing_jobdescription_selector():
    raw = "<html><body><div class=\"cw-summary\"><li><span>City</span><span>Pune</span></li></div></body></html>"
    result = fetch_zoho_detail_from_html(raw, "https://wynploy.zohorecruit.in/jobs/Careers/1/Unhydrated")
    assert result.error_code == ERR_DESCRIPTION_MISSING
    assert result.description is None


def test_fetch_zoho_detail_from_html_rejects_too_short_description():
    raw = (
        "<div class=\"cw-summary\"><ul><li><span>City</span><span>Pune</span></li></ul></div>"
        "<div class=\"cw-jobdescription\"><p>Too short.</p></div>"
    )
    result = fetch_zoho_detail_from_html(raw, "https://wynploy.zohorecruit.in/jobs/Careers/1/Short")
    assert result.error_code == ERR_DESCRIPTION_INVALID


def test_fetch_zoho_detail_from_html_empty_raw_html():
    result = fetch_zoho_detail_from_html("", "https://wynploy.zohorecruit.in/jobs/Careers/1/Empty")
    assert result.error_code == ERR_DESCRIPTION_MISSING
