import re
from datetime import datetime
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

IST_TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(IST_TIMEZONE)

ANCHOR_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

DEFAULT_ANCHOR_TIME = "18:00"

ALLOWED_INTERVAL_HOURS = (6, 12, 24)


def is_valid_anchor_time(value: str) -> bool:
    """Strict HH:mm check: zero-padded hour 00-23 and minute 00-59."""
    return isinstance(value, str) and bool(ANCHOR_TIME_PATTERN.match(value))


def parse_anchor_time(anchor_time: str) -> Tuple[int, int]:
    if not is_valid_anchor_time(anchor_time):
        raise ValueError(f"Invalid anchor time format: {anchor_time!r}. Expected strict HH:mm.")
    hour_str, minute_str = anchor_time.split(":")
    return int(hour_str), int(minute_str)


def compute_aligned_hours(anchor_hour: int, interval_hours: int) -> List[int]:
    """Hours-of-day (0-23) at which the phase-aligned recurrence fires for a
    given anchor hour and interval, e.g. anchor_hour=18, interval=6 ->
    [0, 6, 12, 18]. Requires interval_hours to evenly divide 24."""
    if interval_hours not in ALLOWED_INTERVAL_HOURS:
        raise ValueError(f"interval_hours must be one of {ALLOWED_INTERVAL_HOURS}, got {interval_hours}")
    return sorted((anchor_hour + n * interval_hours) % 24 for n in range(24 // interval_hours))


def build_pipeline_trigger(anchor_time: str, interval_hours: int) -> CronTrigger:
    """Build a phase-aligned CronTrigger for the automated pipeline job.

    The recurrence is anchor + N * interval within each 24h IST day, so restarts,
    delayed completions, or settings saves never shift future cadence.
    """
    anchor_hour, anchor_minute = parse_anchor_time(anchor_time)
    hours = compute_aligned_hours(anchor_hour, interval_hours)
    return CronTrigger(
        hour=",".join(str(h) for h in hours),
        minute=anchor_minute,
        timezone=IST_TIMEZONE,
    )


def next_aligned_run_after(anchor_time: str, interval_hours: int, now: Optional[datetime] = None) -> datetime:
    """First phase-aligned run strictly after `now` (defaults to current IST time).

    A bare CronTrigger queried with previous_fire_time=None can return `now`
    itself when `now` lands exactly on an aligned boundary. Passing `now` as
    both the previous fire time and the cursor forces APScheduler to compute
    the *next* occurrence after that instant, never the instant itself.
    """
    if now is None:
        now = datetime.now(IST)
    trigger = build_pipeline_trigger(anchor_time, interval_hours)
    next_run = trigger.get_next_fire_time(now, now)
    assert next_run > now
    return next_run
