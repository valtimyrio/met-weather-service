from fastapi.testclient import TestClient

from met_weather_service.main import app


def test_invalid_timezone_returns_422() -> None:
    client = TestClient(app)
    resp = client.get("/v1/forecast", params={"tz": "NoSuch/Zone", "at": "14:00"})
    assert resp.status_code == 422


def test_invalid_time_returns_422() -> None:
    client = TestClient(app)
    resp = client.get("/v1/forecast", params={"tz": "UTC", "at": "99:99"})
    assert resp.status_code == 422


def test_time_requires_strict_hhmm_format() -> None:
    client = TestClient(app)

    resp = client.get("/v1/forecast", params={"tz": "UTC", "at": "14:0"})
    assert resp.status_code == 422

    resp = client.get("/v1/forecast", params={"tz": "UTC", "at": "1:00"})
    assert resp.status_code == 422

    resp = client.get("/v1/forecast", params={"tz": "UTC", "at": "14-00"})
    assert resp.status_code == 422


def test_lat_lon_ranges_are_validated() -> None:
    client = TestClient(app)

    resp = client.get("/v1/forecast", params={"lat": 91, "lon": 0})
    assert resp.status_code == 422

    resp = client.get("/v1/forecast", params={"lat": -91, "lon": 0})
    assert resp.status_code == 422

    resp = client.get("/v1/forecast", params={"lat": 0, "lon": 181})
    assert resp.status_code == 422

    resp = client.get("/v1/forecast", params={"lat": 0, "lon": -181})
    assert resp.status_code == 422
