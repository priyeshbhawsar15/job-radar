import pytest

from job_radar.services.settings_store import AppSettingsModel


@pytest.mark.parametrize("valid_value", [6, 12, 24, None])
def test_app_settings_model_accepts_valid_interval_hours(valid_value):
    model = AppSettingsModel(scheduler_interval_hours=valid_value)
    assert model.scheduler_interval_hours == valid_value


@pytest.mark.parametrize("invalid_value", [5, 0, 8, 1, 23, -6])
def test_app_settings_model_rejects_invalid_interval_hours(invalid_value):
    with pytest.raises(ValueError):
        AppSettingsModel(scheduler_interval_hours=invalid_value)
