from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from job_radar.services import settings_store
from job_radar.services.scheduler import SchedulerService
from job_radar.services.scheduler_alignment import next_aligned_run_after
from job_radar.services.settings_store import AppSettingsModel, save_settings

IST = ZoneInfo("Asia/Kolkata")

pytestmark = pytest.mark.asyncio


@pytest.fixture
def isolated_settings_file(tmp_path, monkeypatch):
    monkeypatch.delenv("SETTINGS_FILE_PATH", raising=False)
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(settings_store, "DEFAULT_CONFIG_PATH", path)
    return path


@pytest.fixture
async def scheduler_service_instance(isolated_settings_file):
    save_settings(AppSettingsModel())  # scheduler disabled by default: start() won't schedule a run
    svc = SchedulerService()
    svc.start()
    yield svc
    svc.shutdown()


async def test_sync_pipeline_job_disabled_removes_job(scheduler_service_instance):
    save_settings(AppSettingsModel(scheduler_enabled=False, scheduler_interval_hours=6))
    scheduler_service_instance.sync_pipeline_job()
    assert scheduler_service_instance.scheduler.get_job("automated_pipeline_job") is None


async def test_sync_pipeline_job_no_interval_removes_job(scheduler_service_instance):
    save_settings(AppSettingsModel(scheduler_enabled=True, scheduler_interval_hours=None))
    scheduler_service_instance.sync_pipeline_job()
    assert scheduler_service_instance.scheduler.get_job("automated_pipeline_job") is None


@pytest.mark.parametrize("interval_hours", [6, 12, 24])
async def test_sync_pipeline_job_enabled_schedules_job(scheduler_service_instance, interval_hours):
    save_settings(
        AppSettingsModel(
            scheduler_enabled=True,
            scheduler_interval_hours=interval_hours,
            scheduler_anchor_time="18:30",
        )
    )
    scheduler_service_instance.sync_pipeline_job()
    job = scheduler_service_instance.scheduler.get_job("automated_pipeline_job")
    assert job is not None
    assert job.next_run_time is not None


async def test_sync_pipeline_job_no_immediate_run_on_startup(scheduler_service_instance):
    save_settings(
        AppSettingsModel(
            scheduler_enabled=True,
            scheduler_interval_hours=6,
            scheduler_anchor_time="18:30",
        )
    )
    before = datetime.now(IST)
    scheduler_service_instance.sync_pipeline_job()
    job = scheduler_service_instance.scheduler.get_job("automated_pipeline_job")
    assert job.next_run_time > before + timedelta(seconds=1)


async def test_sync_pipeline_job_non_hour_anchor_minute_preserved(scheduler_service_instance):
    save_settings(
        AppSettingsModel(
            scheduler_enabled=True,
            scheduler_interval_hours=12,
            scheduler_anchor_time="18:30",
        )
    )
    scheduler_service_instance.sync_pipeline_job()
    job = scheduler_service_instance.scheduler.get_job("automated_pipeline_job")
    assert job.next_run_time.astimezone(IST).minute == 30


async def test_sync_pipeline_job_resync_does_not_shift_cadence(scheduler_service_instance):
    """Repeated syncs (simulating restarts or unrelated settings saves) with the
    same settings must resolve to the same phase-aligned next run time."""
    save_settings(
        AppSettingsModel(
            scheduler_enabled=True,
            scheduler_interval_hours=6,
            scheduler_anchor_time="18:30",
        )
    )
    scheduler_service_instance.sync_pipeline_job()
    first_next_run = scheduler_service_instance.scheduler.get_job("automated_pipeline_job").next_run_time

    scheduler_service_instance.sync_pipeline_job()
    second_next_run = scheduler_service_instance.scheduler.get_job("automated_pipeline_job").next_run_time

    assert first_next_run == second_next_run


async def test_sync_pipeline_job_next_run_time_is_strictly_future_on_boundary(
    scheduler_service_instance, monkeypatch
):
    """If sync_pipeline_job runs exactly at an aligned boundary, next_run_time
    must be the strictly-future aligned run, not the current instant."""
    boundary = datetime(2026, 8, 28, 18, 0, 0, tzinfo=IST)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return boundary if tz is not None else boundary.replace(tzinfo=None)

    monkeypatch.setattr(
        "job_radar.services.scheduler_alignment.datetime", _FixedDateTime
    )

    save_settings(
        AppSettingsModel(
            scheduler_enabled=True,
            scheduler_interval_hours=6,
            scheduler_anchor_time="18:00",
        )
    )
    scheduler_service_instance.sync_pipeline_job()
    job = scheduler_service_instance.scheduler.get_job("automated_pipeline_job")

    assert job.next_run_time > boundary
    assert job.next_run_time.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") == "2026-08-29 00:00:00"
    assert job.next_run_time == next_aligned_run_after("18:00", 6, now=boundary)
