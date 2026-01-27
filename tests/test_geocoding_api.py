import httpx
import respx
from fastapi.testclient import TestClient

from met_weather_service.core.config import get_settings
from met_weather_service.main import app
from met_weather_service.services import geocoder_gateway

NOMINATIM = "https://nominatim.openstreetmap.org"
SEARCH_URL = f"{NOMINATIM}/search"
REVERSE_URL = f"{NOMINATIM}/reverse"


@respx.mock
def test_geocode_forward_ok(monkeypatch) -> None:
    geocoder_gateway.clear_cache()
    monkeypatch.setenv("GEOCODER_BASE_URL", NOMINATIM)
    monkeypatch.setenv("GEOCODER_CACHE_TTL_S", "3600")
    monkeypatch.setenv("GEOCODER_RL_MAX_CALLS", "10")
    monkeypatch.setenv("GEOCODER_RL_PERIOD_S", "1")
    get_settings.cache_clear()

    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "display_name": "Belgrade, City of Belgrade, Central Serbia, Serbia",
                    "lat": "44.8125",
                    "lon": "20.4612",
                    "address": {"city": "Belgrade", "country": "Serbia", "state": "Central Serbia"},
                }
            ],
        )
    )

    client = TestClient(app)
    r = client.get("/v1/geocode", params={"q": "Belgrade", "limit": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "Belgrade"
    assert len(body["results"]) == 1
    assert "Belgrade" in body["results"][0]["display_name"]


@respx.mock
def test_reverse_ok(monkeypatch) -> None:
    geocoder_gateway.clear_cache()
    monkeypatch.setenv("GEOCODER_BASE_URL", NOMINATIM)
    monkeypatch.setenv("GEOCODER_CACHE_TTL_S", "3600")
    monkeypatch.setenv("GEOCODER_RL_MAX_CALLS", "10")
    monkeypatch.setenv("GEOCODER_RL_PERIOD_S", "1")
    get_settings.cache_clear()

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
    r = client.get("/v1/reverse", params={"lat": 44.81259, "lon": 20.46129})
    assert r.status_code == 200
    body = r.json()
    assert body["place"]["city"] == "Belgrade"
