import httpx
import respx
from fastapi.testclient import TestClient

from met_weather_service.core.config import get_settings
from met_weather_service.main import app
from met_weather_service.services import met_gateway

MET_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


def _payload() -> dict:
    return {
        "properties": {
            "meta": {"updated_at": "2026-01-26T17:15:58Z", "units": {"air_temperature": "celsius"}},
            "timeseries": [
                {"time": "2026-01-26T13:00:00Z", "data": {"instant": {"details": {"air_temperature": 2.0}}}},
            ],
        }
    }


@respx.mock
def test_rate_limit_blocks_second_upstream_call(monkeypatch) -> None:
    met_gateway.clear_cache()

    # Force upstream call each time
    monkeypatch.setenv("MET_CACHE_TTL_S", "0")

    # Allow only 1 upstream call per 60s (per process)
    monkeypatch.setenv("MET_RL_MAX_CALLS", "1")
    monkeypatch.setenv("MET_RL_PERIOD_S", "60")

    get_settings.cache_clear()

    route = respx.get(MET_URL).mock(return_value=httpx.Response(200, json=_payload()))

    client = TestClient(app)

    r1 = client.get("/v1/forecast")
    assert r1.status_code == 200

    r2 = client.get("/v1/forecast")
    assert r2.status_code == 429
    assert r2.json()["detail"] == "Too many requests"

    assert len(route.calls) == 1
