"""Regressions from the October 11 captured public detail responses."""

import json
from pathlib import Path

import httpx
import pytest

from job_radar.services.detail_extractor import DetailExtractor, description_is_valid


EVIDENCE = Path(__file__).parent / "fixtures" / "detail_failure_20261011"


class NoBrowser:
    async def fetch_board_html(self, *_args, **_kwargs):
        raise RuntimeError("browser deliberately disabled in isolated test")


@pytest.mark.parametrize(
    ("board", "fixture"),
    [
        ("Marriott Tech", "marriott_tech_description_invalid.clean.txt"),
        ("McD", "mcd_description_invalid.clean.txt"),
        ("Redis", "redis_description_invalid.clean.txt"),
        ("Supabase", "supabase_description_invalid.clean.txt"),
        ("BrowserStack", "browserstack_description_missing.raw"),
        ("Vanguard", "vanguard_description_missing.raw"),
    ],
)
def test_captured_role_sections_are_valid_without_losing_qualifications(board, fixture):
    from job_radar.services.detail_extractor import normalize_detail_sections

    original = (EVIDENCE / fixture).read_text()
    if fixture.endswith(".raw"):
        from job_radar.services.workday_detail import clean_workday_html

        original = clean_workday_html(json.loads(original)["jobPostingInfo"]["jobDescription"])
    assert not description_is_valid(original)
    normalized = normalize_detail_sections(original, board)
    assert description_is_valid(normalized)
    assert len(normalized) >= len(original)


@pytest.mark.asyncio
async def test_native_content_failure_survives_failed_public_fallback():
    payload = json.loads((EVIDENCE / "twilio.json").read_text())

    def handler(request):
        if request.url.host == "boards-api.greenhouse.io":
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await DetailExtractor(NoBrowser()).fetch_and_enrich(
            "https://job-boards.greenhouse.io/twilio/jobs/8249194",
            "Twilio", payload["title"], family="greenhouse",
            provider_config={}, client=client,
        )
    assert result.error_code == "description_invalid"


def test_short_workday_and_future_pool_stay_rejected():
    from job_radar.services.detail_extractor import normalize_detail_sections

    for board, fixture in [
        ("Levi Strauss", "levi_strauss_description_missing.clean.txt"),
        ("Camunda", "camunda_description_invalid.clean.txt"),
    ]:
        text = normalize_detail_sections((EVIDENCE / fixture).read_text(), board)
        assert not description_is_valid(text)


@pytest.mark.parametrize(
    ("board", "slug", "accepted"),
    [
        ("Amgen", "amgen", True),
        ("BrowserStack", "browserstack", True),
        ("JLL", "jll", True),
        ("JioStar", "jiostar", True),
        ("Levi Strauss", "levi_strauss", False),
        ("Regal Rexnord", "regal_rexnord", True),
        ("Salesforce", "salesforce", True),
        ("TP", "tp", False),
        ("Vanguard", "vanguard", True),
        ("Walmart", "walmart", True),
    ],
)
def test_exact_workday_cleaner_and_scoped_boundaries(board, slug, accepted):
    from job_radar.services.workday_detail import clean_workday_html
    from job_radar.services.detail_extractor import normalize_detail_sections

    payload = json.loads((EVIDENCE / f"{slug}_description_missing.raw").read_text())
    native = clean_workday_html(payload["jobPostingInfo"]["jobDescription"])
    assert not description_is_valid(native)
    assert description_is_valid(normalize_detail_sections(native, board)) is accepted


def test_jiostar_short_cxs_description_remains_invalid():
    from job_radar.services.workday_detail import clean_workday_html
    from job_radar.services.detail_extractor import normalize_detail_sections

    payload = json.loads((EVIDENCE / "jiostar_invalid_detail_url.raw").read_text())
    native = clean_workday_html(payload["jobPostingInfo"]["jobDescription"])
    assert not description_is_valid(normalize_detail_sections(native, "JioStar"))


@pytest.mark.parametrize(
    ("board", "number", "parser", "required"),
    [
        ("apple", "200314122", "apple", ("Responsibilities", "Minimum Qualifications", "Preferred Qualifications")),
        ("apple", "200314015", "apple", ("Responsibilities", "Minimum Qualifications", "Preferred Qualifications")),
        ("amazon", "10574853", "amazon", ("Key job responsibilities", "Basic Qualifications", "Preferred Qualifications")),
        ("amazon", "10575334", "amazon", ("Key job responsibilities", "Basic Qualifications", "Preferred Qualifications")),
        ("novartis", "10087247", "novartis", ("Summary", "About the Role", "Key Responsibilities")),
        ("novartis", "10088115", "novartis", ("Summary", "About the Role", "Key Responsibilities")),
    ],
)
def test_public_page_sections_preserve_complete_role_and_exact_identity(board, number, parser, required):
    from job_radar.services.apple_detail import parse_apple_detail
    from job_radar.services.site_detail import parse_amazon_detail, parse_novartis_detail

    index = 1 if number in {"200314122", "10574853", "10087247"} else 2
    html = (EVIDENCE / f"{board}_{index}.html").read_text()
    url = {
        "apple": f"https://jobs.apple.com/en-in/details/{number}/captured-role",
        "amazon": f"https://www.amazon.jobs/en/jobs/{number}",
        "novartis": f"https://www.novartis.com/in-en/careers/career-search/job/details/req-{number}-captured-role",
    }[board]
    function = {"apple": parse_apple_detail, "amazon": parse_amazon_detail, "novartis": parse_novartis_detail}[parser]
    result = function(html, url)
    assert result.error_code is None
    assert result.title
    assert description_is_valid(result.description)
    assert all(heading in result.description for heading in required)
    assert function(html, url.replace(number, "99999999")).error_code is not None


@pytest.mark.parametrize(
    ("index", "slug"),
    [
        (1, "118302093231432390-senior-software-engineer-full-stack-google-cloud"),
        (2, "84604442862592710-senior-software-engineer-tech-lead-android-studio"),
    ],
)
def test_google_exact_panel_includes_identity_location_and_qualifications(index, slug):
    from job_radar.services.google_detail import parse_google_detail

    html = (EVIDENCE / f"google_{index}.html").read_text()
    url = "https://www.google.com/about/careers/applications/jobs/results/" + slug
    result = parse_google_detail(html, url)
    assert result.error_code is None
    assert result.location and "India" in result.location
    assert all(part in result.description for part in ("Minimum qualifications", "Preferred qualifications", "About the job", "Responsibilities"))
    assert parse_google_detail(html, url.replace(slug.split("-")[0], "99999999999999999")).error_code == "invalid_payload"


@pytest.mark.parametrize("fixture", [
    "board-godaddy-7882535003-supplemental.json",
    "board-godaddy-8008788003-supplemental.json",
    "board-highradius-7701519003-supplemental.json",
    "board-highradius-7724350003-supplemental.json",
])
def test_greenhouse_scoped_role_and_qualification_boundaries(fixture):
    from job_radar.services.detail_extractor import clean_html_to_text, normalize_detail_sections

    payload = json.loads((EVIDENCE / fixture).read_text())
    board = "GoDaddy" if "godaddy" in fixture else "HighRadius"
    native = clean_html_to_text(payload["content"])
    normalized = normalize_detail_sections(native, board)
    assert not description_is_valid(native)
    assert description_is_valid(normalized)
    assert "Responsibilities" in normalized
    assert "Qualifications" in normalized


@pytest.mark.parametrize(("index", "number", "listing_title"), [
    (1, "7986348003", "Analytics Engineer — Data Analytics & Transformation (DAT)"),
    (2, "7562947003", "Deployment Engineer"),
])
def test_celonis_observed_api_contract_and_stable_id_title_update(index, number, listing_title):
    from job_radar.services.celonis_detail import parse_celonis_detail
    from job_radar.services.detail_contracts import DetailRequest

    payload = json.loads((EVIDENCE / f"celonis_{index}.json").read_text())
    request = DetailRequest("celonis_dxp", f"https://careers.celonis.com/join-us/open-positions/job-detail?jobId={number}", "Celonis", listing_title, {})
    result = parse_celonis_detail(payload, request)
    assert result.error_code is None
    assert description_is_valid(result.description)
    assert "Qualifications" in result.description
    assert result.location == "Bangalore, India"
    assert parse_celonis_detail({**payload, "id": "9999999999"}, request).error_code == "identity_mismatch"
    assert parse_celonis_detail(payload, DetailRequest(request.family, request.public_url, request.board_name, "Unrelated role", {})).error_code == "identity_mismatch"


@pytest.mark.parametrize("number", ["346891", "346903"])
def test_oracle_exact_requisition_preserves_duties_and_skills(number):
    from job_radar.services.oracle_detail import find_oracle_item, compose_oracle_description
    from job_radar.services.detail_extractor import normalize_detail_sections

    payload = json.loads((EVIDENCE / f"oracle-{number}.json").read_text())
    item = find_oracle_item(payload, number)
    assert item is not None
    native = compose_oracle_description(item)
    assert not description_is_valid(native)
    normalized = normalize_detail_sections(native, "Oracle")
    assert description_is_valid(normalized)
    assert "Job Responsibilities" in normalized and "Mandatory Skills" in normalized
    assert find_oracle_item(payload, "999999") is None


@pytest.mark.parametrize(("board", "slug", "accepted"), [
    ("Sourcegraph", "sourcegraph", True),
    ("Razorpay", "razorpay", True),
    ("Cognite", "cognite", True),
    ("Gitlab", "gitlab", True),
    ("Coinbase", "coinbase", True),
    ("Groww", "groww", True),
    ("Twilio", "twilio", False),
    ("Airbnb", "airbnb", True),
    ("Druva", "druva", False),
])
def test_other_greenhouse_native_content_with_restrictive_controls(board, slug, accepted):
    from job_radar.services.detail_extractor import clean_html_to_text, normalize_detail_sections

    payload = json.loads((EVIDENCE / f"{slug}.json").read_text())
    native = clean_html_to_text(payload["content"])
    normalized = normalize_detail_sections(native, board)
    assert not description_is_valid(native)
    assert description_is_valid(normalized) is accepted
    if accepted:
        assert "Responsibilities" in normalized and "Qualifications" in normalized


def test_mattel_exact_page_retains_conflicting_worksite_and_control_passes():
    from job_radar.services.mattel_detail import parse_mattel_detail
    from job_radar.services.detail_contracts import DetailRequest

    failed = DetailRequest("custom", "https://jobs.mattel.com/en/job/hyderabad/sr-electronic-engineer/2015/90860268592", "Mattel", "Sr Electronic Engineer Hyderabad, Telangana 10/08/2026", {})
    control = DetailRequest("custom", "https://jobs.mattel.com/en/job/hyderabad/sr-software-engineer/2015/94318565728", "Mattel", "Sr Software Engineer Hyderabad, Telangana 04/24/2026", {})
    conflict = parse_mattel_detail((EVIDENCE / "mattel_1.html").read_text(), failed)
    accepted = parse_mattel_detail((EVIDENCE / "mattel_2.html").read_text(), control)
    assert conflict.error_code == "location_conflict"
    assert conflict.location == "Belagavi, India (Aequs Facility)"
    assert "What Your Impact Will Be" in conflict.description
    assert description_is_valid(conflict.description)
    assert accepted.error_code is None and accepted.location == "Hyderabad"
    assert parse_mattel_detail((EVIDENCE / "mattel_1.html").read_text(), DetailRequest("custom", control.public_url, "Mattel", failed.title, {})).error_code == "identity_mismatch"


def test_tesco_narrative_duties_and_second_body_title_conflict():
    from job_radar.services.tesco_detail import parse_tesco_detail
    from job_radar.services.detail_contracts import DetailRequest

    first = DetailRequest("avature", "https://careers.tesco.com/en_GB/careers/JobDetail/Principal-Software-Development-Engineer/141645", "Tesco", "Principal Software Development Engineer", {})
    second = DetailRequest("avature", "https://careers.tesco.com/en_GB/careers/JobDetail/Software-Development-Engineer-II/167053", "Tesco", "Software Development Engineer II", {})
    good = parse_tesco_detail((EVIDENCE / "tesco_1.html").read_text(), first)
    mismatch = parse_tesco_detail((EVIDENCE / "tesco_2.html").read_text(), second)
    assert good.error_code is None and description_is_valid(good.description)
    assert "Experience relevant for this job" in good.description
    assert "Qualifications" in good.description
    assert mismatch.error_code == "identity_mismatch"
    assert parse_tesco_detail((EVIDENCE / "tesco_1.html").read_text(), second).error_code == "identity_mismatch"
    # A long company narrative without the observed role-led duties is insufficient.
    company_only = (EVIDENCE / "tesco_1.html").read_text().replace(
        "As a Principal Software Development Engineer, you", "At Tesco Technology, we"
    )
    assert parse_tesco_detail(company_only, first).error_code == "description_invalid"


def test_second_workday_and_greenhouse_samples_retain_restrictive_outcomes():
    from job_radar.services.workday_detail import clean_workday_html
    from job_radar.services.detail_extractor import clean_html_to_text, normalize_detail_sections

    for board, fixture, expected in [
        ("Regal Rexnord", "regal_rexnord_second.raw", True),
        ("TP", "tp_second.raw", False),
    ]:
        payload = json.loads((EVIDENCE / fixture).read_text())
        native = clean_workday_html(payload["jobPostingInfo"]["jobDescription"])
        assert description_is_valid(normalize_detail_sections(native, board)) is expected
    for board, fixture, expected in [("Databricks", "databricks_second.json", False), ("Twilio", "twilio_second.json", True)]:
        payload = json.loads((EVIDENCE / fixture).read_text())
        native = clean_html_to_text(payload["content"])
        assert description_is_valid(normalize_detail_sections(native, board), title=payload["title"]) is expected


def test_databricks_japanese_duties_are_bounded_before_requirements():
    from job_radar.services.detail_extractor import clean_html_to_text

    payload = json.loads((EVIDENCE / "databricks.json").read_text())
    native = clean_html_to_text(payload["content"])
    assert not description_is_valid(native, title=payload["title"])
    assert description_is_valid(native, title=payload["title"], board_name="Databricks")
    company_and_requirements = native.split("あなたがもたらす影響")[0] + "あなたがもたらす影響\n" + native.split("必要な条件/経験", 1)[-1]
    assert not description_is_valid(company_and_requirements, title=payload["title"], board_name="Databricks")
