import httpx
import respx
from fastapi.testclient import TestClient

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
def test_forecast_cache_hit_makes_single_upstream_call(monkeypatch) -> None:
    met_gateway.clear_cache()
    monkeypatch.setenv("MET_CACHE_TTL_S", "300")
    from met_weather_service.core.config import get_settings
    get_settings.cache_clear()

    route = respx.get(MET_URL).mock(
        return_value=httpx.Response(200, json=_payload(), headers={"Last-Modified": "Mon, 26 Jan 2026 12:00:00 GMT"}))

    from met_weather_service.main import app
    client = TestClient(app)

    r1 = client.get("/v1/forecast")
    assert r1.status_code == 200

    r2 = client.get("/v1/forecast")
    assert r2.status_code == 200

    assert route.called
    assert len(route.calls) == 1


@respx.mock
def test_forecast_revalidates_with_if_modified_since_and_handles_304(monkeypatch) -> None:
    met_gateway.clear_cache()
    monkeypatch.setenv("MET_CACHE_TTL_S", "10")
    from met_weather_service.core.config import get_settings
    get_settings.cache_clear()

    last_mod = "Mon, 26 Jan 2026 12:00:00 GMT"

    t = {"now": 1000.0}

    def fake_time() -> float:
        return t["now"]

    monkeypatch.setattr(met_gateway.time, "time", fake_time)

    req1 = httpx.Request("GET", MET_URL)
    resp1 = httpx.Response(200, request=req1, json=_payload(), headers={"Last-Modified": last_mod})

    req2 = httpx.Request("GET", MET_URL)
    resp2 = httpx.Response(304, request=req2, headers={})

    route = respx.get(MET_URL).mock(side_effect=[resp1, resp2])

    from met_weather_service.main import app
    client = TestClient(app)

    r1 = client.get("/v1/forecast")
    assert r1.status_code == 200
    body1 = r1.json()

    t["now"] = 1011.0

    r2 = client.get("/v1/forecast")
    assert r2.status_code == 200
    body2 = r2.json()

    assert body2 == body1

    assert len(route.calls) == 2
    ims = route.calls[1].request.headers.get("If-Modified-Since")
    assert ims == last_mod
