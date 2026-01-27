import httpx
import respx
from fastapi.testclient import TestClient

from met_weather_service.core.config import get_settings
from met_weather_service.main import app
from met_weather_service.services import geocoder_gateway, met_gateway

MET_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
NOMINATIM = "https://nominatim.openstreetmap.org"
REVERSE_URL = f"{NOMINATIM}/reverse"


def _met_payload() -> dict:
    return {
        "properties": {
            "meta": {"updated_at": "2026-01-26T17:15:58Z", "units": {"air_temperature": "celsius"}},
            "timeseries": [
                {"time": "2026-01-26T13:00:00Z", "data": {"instant": {"details": {"air_temperature": 2.0}}}},
            ],
        }
    }


@respx.mock
def test_forecast_include_place_adds_location_fields(monkeypatch) -> None:
    met_gateway.clear_cache()
    geocoder_gateway.clear_cache()

    monkeypatch.setenv("MET_CACHE_TTL_S", "0")
    monkeypatch.setenv("GEOCODER_BASE_URL", NOMINATIM)
    monkeypatch.setenv("GEOCODER_CACHE_TTL_S", "3600")
    monkeypatch.setenv("GEOCODER_RL_MAX_CALLS", "10")
    monkeypatch.setenv("GEOCODER_RL_PERIOD_S", "1")
    get_settings.cache_clear()

    respx.get(MET_URL).mock(return_value=httpx.Response(200, json=_met_payload()))
    respx.get(REVERSE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "display_name": "Belgrade, City of Belgrade, Central Serbia, Serbia",
                "lat": "44.8125",
                "lon": "20.4612",
                "address": {"city": "Belgrade", "country": "Serbia", "state": "Central Serbia"},
            },
        )
    )

    client = TestClient(app)
    r = client.get("/v1/forecast", params={"include_place": "true"})
    assert r.status_code == 200
    body = r.json()

    loc = body["location"]
    assert "Belgrade" in loc["place_name"]
    assert loc["city"] == "Belgrade"
    assert loc["country"] == "Serbia"
