import pytest
from met_weather_service.core.config import get_settings


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch) -> None:
    """
    Ensure required environment variables are set for tests.

    MET_USER_AGENT is required by MetClient runtime checks.
    We set it explicitly here to avoid dependence on system env.
    """
    monkeypatch.setenv(
        "MET_USER_AGENT",
        "met-weather-service-tests/0.1 (pytest)",
    )

    # Clear cached Settings so env changes take effect
    get_settings.cache_clear()
