import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from job_radar.services.scheduler_alignment import (
    DEFAULT_ANCHOR_TIME,
    build_pipeline_trigger,
    compute_aligned_hours,
    is_valid_anchor_time,
    next_aligned_run_after,
    parse_anchor_time,
)

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    "value",
    ["00:00", "18:00", "23:59", "06:30", "09:05"],
)
def test_valid_anchor_times(value):
    assert is_valid_anchor_time(value) is True


@pytest.mark.parametrize(
    "value",
    ["24:00", "18:60", "9:05", "18:5", "1800", "18-00", "", "abc", "18:00:00", "-1:00"],
)
def test_invalid_anchor_times(value):
    assert is_valid_anchor_time(value) is False


def test_parse_anchor_time():
    assert parse_anchor_time("18:30") == (18, 30)
    assert parse_anchor_time(DEFAULT_ANCHOR_TIME) == (18, 0)


def test_parse_anchor_time_raises_on_invalid():
    with pytest.raises(ValueError):
        parse_anchor_time("24:00")


@pytest.mark.parametrize(
    "anchor_hour,interval_hours,expected",
    [
        (18, 6, [0, 6, 12, 18]),
        (18, 12, [6, 18]),
        (18, 24, [18]),
        (0, 6, [0, 6, 12, 18]),
        (23, 6, [5, 11, 17, 23]),
    ],
)
def test_compute_aligned_hours(anchor_hour, interval_hours, expected):
    assert compute_aligned_hours(anchor_hour, interval_hours) == expected


def test_compute_aligned_hours_rejects_unsupported_interval():
    with pytest.raises(ValueError):
        compute_aligned_hours(18, 5)


def test_build_pipeline_trigger_1830_6h_alignment():
    trigger = build_pipeline_trigger("18:30", 6)
    now = datetime(2026, 8, 28, 0, 0, tzinfo=IST)
    fire_times = []
    previous = None
    cursor = now
    for _ in range(4):
        cursor = trigger.get_next_fire_time(previous, cursor)
        fire_times.append(cursor.astimezone(IST).strftime("%H:%M"))
        previous = cursor
    assert fire_times == ["00:30", "06:30", "12:30", "18:30"]


def test_build_pipeline_trigger_1830_12h_alignment():
    trigger = build_pipeline_trigger("18:30", 12)
    now = datetime(2026, 8, 28, 0, 0, tzinfo=IST)
    cursor = now
    previous = None
    fire_times = []
    for _ in range(2):
        cursor = trigger.get_next_fire_time(previous, cursor)
        fire_times.append(cursor.astimezone(IST).strftime("%H:%M"))
        previous = cursor
    assert fire_times == ["06:30", "18:30"]


def test_build_pipeline_trigger_1830_24h_alignment():
    trigger = build_pipeline_trigger("18:30", 24)
    now = datetime(2026, 8, 28, 0, 0, tzinfo=IST)
    next_fire = trigger.get_next_fire_time(None, now)
    assert next_fire.astimezone(IST).strftime("%H:%M") == "18:30"


def test_build_pipeline_trigger_next_run_is_strictly_future_not_immediate():
    trigger = build_pipeline_trigger("18:00", 6)
    now = datetime(2026, 8, 28, 18, 0, tzinfo=IST)
    next_fire = trigger.get_next_fire_time(now, now)
    assert next_fire > now
    assert next_fire.astimezone(IST).strftime("%H:%M") == "00:00"


def test_build_pipeline_trigger_uses_ist_timezone():
    trigger = build_pipeline_trigger("18:00", 24)
    assert str(trigger.timezone) == "Asia/Kolkata"


def test_next_aligned_run_after_exactly_on_boundary_returns_strictly_future():
    now = datetime(2026, 8, 28, 18, 0, 0, tzinfo=IST)
    next_run = next_aligned_run_after("18:00", 6, now=now)
    assert next_run > now
    assert next_run.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") == "2026-08-29 00:00:00"


def test_next_aligned_run_after_just_before_boundary_returns_the_boundary():
    now = datetime(2026, 8, 28, 17, 59, 59, tzinfo=IST)
    next_run = next_aligned_run_after("18:00", 6, now=now)
    assert next_run > now
    assert next_run.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") == "2026-08-28 18:00:00"


def test_next_aligned_run_after_just_after_boundary_returns_next_aligned_hour():
    now = datetime(2026, 8, 28, 18, 0, 1, tzinfo=IST)
    next_run = next_aligned_run_after("18:00", 6, now=now)
    assert next_run > now
    assert next_run.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") == "2026-08-29 00:00:00"


def test_next_aligned_run_after_does_not_shift_phase():
    now = datetime(2026, 8, 28, 3, 0, 0, tzinfo=IST)
    next_run = next_aligned_run_after("18:30", 12, now=now)
    assert next_run.astimezone(IST).strftime("%H:%M:%S") == "06:30:00"
