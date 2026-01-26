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
