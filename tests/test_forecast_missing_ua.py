from fastapi.testclient import TestClient

from met_weather_service.core.config import get_settings
from met_weather_service.main import app


def test_forecast_returns_502_when_user_agent_missing(monkeypatch) -> None:
    monkeypatch.delenv("MET_USER_AGENT", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    resp = client.get("/v1/forecast")

    assert resp.status_code == 502
    assert resp.json()["detail"].startswith("MET upstream error:")
