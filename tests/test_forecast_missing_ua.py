from fastapi.testclient import TestClient

from met_weather_service.core.config import get_settings
from met_weather_service.main import app


def test_forecast_returns_500_when_user_agent_missing(monkeypatch) -> None:
    monkeypatch.delenv("MET_USER_AGENT", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    resp = client.get("/v1/forecast")

    assert resp.status_code == 500
    assert resp.json()["detail"].startswith("MET_USER_AGENT is not set")
