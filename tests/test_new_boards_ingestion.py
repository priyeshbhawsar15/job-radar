import json
import pytest
from pathlib import Path

from job_radar.adapters.registry import adapter_registry
from job_radar.db.seed import INITIAL_BOARDS
from job_radar.services.location import is_india_eligible

FIXTURES_DIR = Path("tests/fixtures")

# Filter to the 65 new boards (from index 37 to end of INITIAL_BOARDS)
NEW_BOARDS = INITIAL_BOARDS[37:]

NAME_MAP = {
    "phonepay": "phonepe",
    "hobspot": "hubspot",
    "godaddy": "godaddy",
    "workday": "workdaycorp",
    "publicis_sapient": "publicissapient",
}


def get_board_fixture_path(board_name: str, family: str) -> Path:
    raw_clean = board_name.lower().replace(" ", "_").replace(".", "").replace("-", "_")
    clean_name = NAME_MAP.get(raw_clean, raw_clean)
    return FIXTURES_DIR / family / f"{clean_name}.json"


def test_65_new_boards_registered_count():
    assert len(NEW_BOARDS) == 65
    assert len(INITIAL_BOARDS) == 102


@pytest.mark.parametrize("board_tuple", NEW_BOARDS, ids=lambda b: b[1])
def test_board_adapter_and_fixture_parsing(board_tuple):
    b_id, name, family, target_url = board_tuple[0], board_tuple[1], board_tuple[2], board_tuple[3]

    adapter = adapter_registry.get(family)
    assert adapter is not None, f"Adapter for family '{family}' not found in registry"

    fixture_path = get_board_fixture_path(name, family)
    assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"

    payload_text = fixture_path.read_text()

    extracted = adapter.parse_raw_payload(
        payload=payload_text,
        board_name=name,
        target_url=target_url
    )

    assert isinstance(extracted, list), f"Expected list of ExtractedCandidate for {name}"
    assert len(extracted) > 0, f"Expected at least 1 extracted candidate for {name}"

    for candidate in extracted:
        assert candidate.title, f"Candidate missing title for board {name}"
        assert candidate.company == name, f"Mismatch company for board {name}"
        assert candidate.raw_url, f"Candidate missing raw_url for board {name}"
        assert candidate.fingerprint, f"Candidate missing fingerprint for board {name}"

        # Test India Gate classification on candidate location
        is_eligible, reason = is_india_eligible(candidate.location)
        if is_eligible:
            assert reason is None
        else:
            assert reason is not None
            assert "NON_INDIA_LOCATION" in reason


def test_india_gate_edge_cases_on_candidates():
    # Non-India location candidate
    eligible_sf, reason_sf = is_india_eligible("San Francisco, CA")
    assert not eligible_sf
    assert "NON_INDIA_LOCATION: San Francisco, CA" in reason_sf

    # India location candidate
    eligible_blr, reason_blr = is_india_eligible("Bengaluru, India")
    assert eligible_blr
    assert reason_blr is None

    # Missing location candidate
    eligible_none, reason_none = is_india_eligible(None)
    assert eligible_none
    assert reason_none is None
