"""Captured role evidence and labelled synthetic section-context regressions."""

import json
from pathlib import Path

import pytest

from job_radar.services.detail_extractor import description_is_valid


_CAPTURE = Path(__file__).parent / "fixtures" / "live_description_validation.jsonl"
_ROWS = [json.loads(line) for line in _CAPTURE.read_text().splitlines()]


@pytest.mark.parametrize("row", _ROWS, ids=lambda row: row["board"])
def test_captured_live_description_role_evidence(row):
    assert description_is_valid(row["description"]) is row["expected_valid"]


@pytest.mark.parametrize("text", [
    # Synthetic: many action words and bullets remain company narrative.
    "About Our Company\n" +
    ("• We build products, develop platforms, design tools, and support customers worldwide.\n" * 8) +
    "Benefits:\n• We provide health coverage and deliver flexible leave for employees.\n",
    # Synthetic: a generic role heading inside navigation has no actual duties.
    "Home\nProducts\nCareers\nResponsibilities\n" +
    ("Explore jobs, browse roles, create a profile, and apply now.\n" * 12),
    # Synthetic: a future-only talent community is not an advertised role.
    "Join our talent community for future opportunities. No current positions.\n" +
    ("Share your profile and we will contact you later.\n" * 12),
])
def test_synthetic_non_role_content_is_rejected(text):
    assert not description_is_valid(text)
