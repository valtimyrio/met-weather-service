from fastapi.testclient import TestClient

from met_weather_service.main import app


def test_ui_root_serves_html() -> None:
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "MET Weather Service" in resp.text


def test_ui_static_js_served() -> None:
    client = TestClient(app)
    resp = client.get("/static/ui.js")
    assert resp.status_code == 200
    assert "fetch(" in resp.text
