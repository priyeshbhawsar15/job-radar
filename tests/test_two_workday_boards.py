import json
from pathlib import Path
import pytest
import httpx
from httpx import AsyncClient, Response

from job_radar.adapters.registry import adapter_registry
from job_radar.db.seed import INITIAL_BOARDS, BLOCKED_BOARD_IDS, build_initial_revision_config
from job_radar.services.workday_detail import (
    parse_workday_cxs_url,
    build_cxs_detail_url,
    fetch_workday_detail,
)
from job_radar.services.detail_contracts import DetailRequest
from job_radar.services.location import evaluate_location

FIXTURES_DIR = Path("tests/fixtures/workday")

LEVI_BOARD_TUPLE = next(b for b in INITIAL_BOARDS if b[0] == "board-levistrauss")
EPICOR_BOARD_TUPLE = next(b for b in INITIAL_BOARDS if b[0] == "board-epicor")


def test_seed_configuration_levi_and_epicor():
    # 1. Registration & Status
    assert LEVI_BOARD_TUPLE[0] == "board-levistrauss"
    assert EPICOR_BOARD_TUPLE[0] == "board-epicor"
    assert LEVI_BOARD_TUPLE[0] not in BLOCKED_BOARD_IDS
    assert EPICOR_BOARD_TUPLE[0] not in BLOCKED_BOARD_IDS

    # 2. URLs & Facets preserved
    assert LEVI_BOARD_TUPLE[3] == (
        "https://levistraussandco.wd5.myworkdayjobs.com/en-US/External"
        "?Location_Country=c4f78be1a8f14da0ab49ce1162348a5e"
        "&jobFamilyGroup=cf6792ac2be9108725fe33775db3593e"
        "&jobFamilyGroup=52c304728b9f10011014dbb434830000"
    )
    assert EPICOR_BOARD_TUPLE[3] == (
        "https://epicorsoftware.wd5.myworkdayjobs.com/epicorjobs"
        "?locations=bac801da606910010b29863a25640000"
        "&locations=e23509d8aa44100205d8750add280000"
        "&jobFamilyGroup=bac801da60691001591dc29c07ac0000"
    )

    # 3. Revision config extras & trusted source scopes
    levi_cfg = build_initial_revision_config(LEVI_BOARD_TUPLE)
    assert levi_cfg.get("source_country_scope") == "IN"
    assert levi_cfg.get("source_scope_evidence") == "workday_location_country_filter"

    epicor_cfg = build_initial_revision_config(EPICOR_BOARD_TUPLE)
    assert epicor_cfg.get("source_country_scope") == "IN"
    assert epicor_cfg.get("source_scope_evidence") == "workday_verified_india_location_filters"


def test_workday_listing_parsing_levi():
    fixture_path = FIXTURES_DIR / "levistrauss.json"
    raw_json = fixture_path.read_text()

    adapter = adapter_registry.get("workday")
    candidates = adapter.parse_raw_payload(
        payload=raw_json,
        board_name="Levi Strauss",
        target_url=LEVI_BOARD_TUPLE[3]
    )

    assert len(candidates) == 17
    sample = candidates[0]
    assert sample.title == "SAP FICO Analyst"
    assert sample.company == "Levi Strauss"
    assert sample.location == "GCC Office – ITC Green Center, Bengaluru, Karnataka, India; Bengaluru, India"
    assert sample.raw_url == "https://levistraussandco.wd5.myworkdayjobs.com/en-US/External/job/GCC-Office--ITC-Green-Center-Bengaluru-Karnataka-India/SAP-FICO-Analyst_R-0156156-1"
    assert sample.fingerprint is not None


def test_workday_listing_parsing_epicor():
    fixture_path = FIXTURES_DIR / "epicor.json"
    raw_json = fixture_path.read_text()

    adapter = adapter_registry.get("workday")
    candidates = adapter.parse_raw_payload(
        payload=raw_json,
        board_name="Epicor",
        target_url=EPICOR_BOARD_TUPLE[3]
    )

    assert len(candidates) == 4
    sample = candidates[0]
    assert sample.title == "Development Operations Analyst"
    assert sample.company == "Epicor"
    assert sample.location == "India, Hyderabad; India, Bangalore"
    assert sample.raw_url == "https://epicorsoftware.wd5.myworkdayjobs.com/epicorjobs/job/India-Bangalore/Development-Operations-Analyst_JR104223"
    assert sample.fingerprint is not None


def test_cxs_detail_url_derivation():
    levi_job_url = "https://levistraussandco.wd5.myworkdayjobs.com/en-US/External/job/GCC-Office--ITC-Green-Center-Bengaluru-Karnataka-India/SAP-FICO-Analyst_R-0156156-1"
    parsed_levi = parse_workday_cxs_url(levi_job_url)
    assert parsed_levi == (
        "levistraussandco",
        "External",
        "GCC-Office--ITC-Green-Center-Bengaluru-Karnataka-India/SAP-FICO-Analyst_R-0156156-1"
    )
    assert build_cxs_detail_url(levi_job_url) == (
        "https://levistraussandco.wd5.myworkdayjobs.com/wday/cxs/levistraussandco/External/job/GCC-Office--ITC-Green-Center-Bengaluru-Karnataka-India/SAP-FICO-Analyst_R-0156156-1"
    )

    epicor_job_url = "https://epicorsoftware.wd5.myworkdayjobs.com/epicorjobs/job/India-Bangalore/Development-Operations-Analyst_JR104223"
    parsed_epicor = parse_workday_cxs_url(epicor_job_url)
    assert parsed_epicor == (
        "epicorsoftware",
        "epicorjobs",
        "India-Bangalore/Development-Operations-Analyst_JR104223"
    )
    assert build_cxs_detail_url(epicor_job_url) == (
        "https://epicorsoftware.wd5.myworkdayjobs.com/wday/cxs/epicorsoftware/epicorjobs/job/India-Bangalore/Development-Operations-Analyst_JR104223"
    )


@pytest.mark.asyncio
async def test_fetch_workday_detail_levi():
    detail_fixture = json.loads((FIXTURES_DIR / "levistrauss_detail.json").read_text())
    levi_job_url = "https://levistraussandco.wd5.myworkdayjobs.com/en-US/External/job/GCC-Office--ITC-Green-Center-Bengaluru-Karnataka-India/SAP-FICO-Analyst_R-0156156-1"

    async def mock_handler(request):
        return Response(200, json=detail_fixture)

    client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    req = DetailRequest(
        family="workday",
        public_url=levi_job_url,
        board_name="Levi Strauss",
        title="SAP FICO Analyst",
        provider_config={}
    )

    res = await fetch_workday_detail(req, client)
    assert res.source == "workday_cxs_detail"
    assert res.title == "SAP FICO Analyst"
    assert res.location == "GCC Office – ITC Green Center, Bengaluru, Karnataka, India"
    assert len(res.description) > 500
    assert "SAP" in res.description


@pytest.mark.asyncio
async def test_fetch_workday_detail_epicor():
    detail_fixture = json.loads((FIXTURES_DIR / "epicor_detail.json").read_text())
    epicor_job_url = "https://epicorsoftware.wd5.myworkdayjobs.com/epicorjobs/job/India-Bangalore/Development-Operations-Analyst_JR104223"

    async def mock_handler(request):
        return Response(200, json=detail_fixture)

    client = AsyncClient(transport=httpx.MockTransport(mock_handler))
    req = DetailRequest(
        family="workday",
        public_url=epicor_job_url,
        board_name="Epicor",
        title="Development Operations Analyst",
        provider_config={}
    )

    res = await fetch_workday_detail(req, client)
    assert res.source == "workday_cxs_detail"
    assert res.title == "Development Operations Analyst"
    assert res.location == "India, Bangalore"
    assert len(res.description) > 500
    assert "Development Operations" in res.description or "Epicor" in res.description


def test_location_classification_decision_system():
    # 1. Levi evaluation
    raw_loc_levi = "GCC Office – ITC Green Center, Bengaluru, Karnataka, India; Bengaluru, India"
    eval_levi = evaluate_location(
        location=raw_loc_levi,
        source_scope="IN",
        source_evidence="workday_location_country_filter"
    )
    assert eval_levi.decision == "INDIA"
    assert eval_levi.eligible is True
    assert eval_levi.confidence == "HIGH"
    assert "workday_location_country_filter" in eval_levi.evidence

    # 2. Epicor evaluation with multi-location raw string
    raw_loc_epicor = "India, Hyderabad; India, Bangalore"
    eval_epicor = evaluate_location(
        location=raw_loc_epicor,
        source_scope="IN",
        source_evidence="workday_verified_india_location_filters"
    )
    assert eval_epicor.decision == "INDIA"
    assert eval_epicor.eligible is True
    assert eval_epicor.confidence == "HIGH"
    assert "workday_verified_india_location_filters" in eval_epicor.evidence
