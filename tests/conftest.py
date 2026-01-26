import pytest
from met_weather_service.core.config import get_settings


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch) -> None:
    """
    Ensure MET_USER_AGENT is set for most tests.
    Individual tests may explicitly delete it.
    """
    monkeypatch.setenv(
        "MET_USER_AGENT",
        "met-weather-service-tests/0.1 (pytest)",
    )
    get_settings.cache_clear()
