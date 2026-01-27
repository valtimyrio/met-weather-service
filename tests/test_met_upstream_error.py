import httpx
import respx
from fastapi.testclient import TestClient

from met_weather_service.main import app

MET_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


@respx.mock
def test_forecast_returns_502_on_connect_error() -> None:
    req = httpx.Request("GET", MET_URL)
    respx.get(MET_URL).mock(side_effect=httpx.ConnectError("boom", request=req))

    client = TestClient(app)
    resp = client.get("/v1/forecast")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "MET upstream error"


@respx.mock
def test_forecast_returns_502_on_http_status_error() -> None:
    req = httpx.Request("GET", MET_URL)
    respx.get(MET_URL).mock(return_value=httpx.Response(429, request=req))

    client = TestClient(app)
    resp = client.get("/v1/forecast")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "MET upstream error"


@respx.mock
def test_forecast_returns_502_on_invalid_json() -> None:
    req = httpx.Request("GET", MET_URL)
    respx.get(MET_URL).mock(
        return_value=httpx.Response(
            200,
            request=req,
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
    )

    client = TestClient(app)
    resp = client.get("/v1/forecast")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "MET upstream error"


@respx.mock
def test_health_met_returns_502_on_timeout() -> None:
    req = httpx.Request("GET", MET_URL)
    respx.get(MET_URL).mock(side_effect=httpx.ReadTimeout("timeout", request=req))

    client = TestClient(app)
    resp = client.get("/health/met")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "MET upstream error"
