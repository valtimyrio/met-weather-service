import httpx
import respx
from fastapi.testclient import TestClient

from met_weather_service.main import app


def _met_payload_two_days() -> dict:
    # 2026-01-26: Belgrade is UTC+1, so 13:00Z == 14:00 local
    # 2026-01-27: same idea
    return {
        "properties": {
            "meta": {"updated_at": "2026-01-26T17:15:58Z", "units": {"air_temperature": "celsius"}},
            "timeseries": [
                # Day 1 candidates
                {"time": "2026-01-26T12:00:00Z", "data": {"instant": {"details": {"air_temperature": 1.0}}}},
                # best for 14:00 local
                {"time": "2026-01-26T13:00:00Z", "data": {"instant": {"details": {"air_temperature": 2.0}}}},
                {"time": "2026-01-26T14:00:00Z", "data": {"instant": {"details": {"air_temperature": 3.0}}}},
                # Day 2 candidates
                # best for 14:00 local
                {"time": "2026-01-27T13:00:00Z", "data": {"instant": {"details": {"air_temperature": 4.0}}}},
                {"time": "2026-01-27T14:00:00Z", "data": {"instant": {"details": {"air_temperature": 5.0}}}},
            ],
        }
    }


@respx.mock
def test_forecast_with_all_params_and_timezone_selection() -> None:
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

    # check truncate, and full request path
    route = respx.get(url).mock(
        return_value=httpx.Response(200, json=_met_payload_two_days())
    )

    client = TestClient(app)

    # values where truncate != round
    resp = client.get(
        "/v1/forecast",
        params={
            "lat": "44.81259",  # truncate -> 44.8125, round -> 44.8126
            "lon": "20.46129",  # truncate -> 20.4612, round -> 20.4613
            "tz": "Europe/Belgrade",
            "at": "14:00",
        },
        headers={"User-Agent": "tests"},
    )

    assert resp.status_code == 200
    body = resp.json()

    assert body["location"]["timezone"] == "Europe/Belgrade"
    assert body["location"]["target_time"] == "14:00"

    # Must reflect the actual MET request coords (truncate), not round
    assert body["location"]["lat"] == 44.8125
    assert body["location"]["lon"] == 20.4612

    days = body["days"]
    assert [d["date"] for d in days] == ["2026-01-26", "2026-01-27"]

    # For 14:00 Europe/Belgrade at winter chooses 13:00Z (14:00+01:00)
    assert days[0]["temperature_c"] == 2.0
    assert days[0]["time"].endswith("+01:00")

    assert days[1]["temperature_c"] == 4.0
    assert days[1]["time"].endswith("+01:00")

    # Check that request really went to MET, aswell as truncated coords
    assert route.called
    req = route.calls[0].request
    params = dict(req.url.params)
    assert params["lat"] == "44.8125"
    assert params["lon"] == "20.4612"
