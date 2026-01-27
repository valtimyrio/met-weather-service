from met_weather_service.services.forecast import iter_met_points


def test_iter_met_points_skips_malformed_entries() -> None:
    data = {
        "properties": {
            "timeseries": [
                {"time": "2026-01-26T13:00:00Z", "data": {"instant": {"details": {"air_temperature": 2.0}}}},
                {"time": "2026-01-26T14:00:00Z", "data": {}},  # missing path
                {"time": "bad-datetime", "data": {"instant": {"details": {"air_temperature": 3.0}}}},
                {"time": "2026-01-26T15:00:00Z", "data": {"instant": {"details": {"air_temperature": "x"}}}},
            ]
        }
    }

    points = list(iter_met_points(data))
    assert len(points) == 1
    assert points[0].temperature_c == 2.0


def test_iter_met_points_accepts_naive_datetime_assuming_utc() -> None:
    data = {
        "properties": {
            "timeseries": [
                # No timezone in string - should be treated as UTC by our code
                {"time": "2026-01-26T13:00:00", "data": {"instant": {"details": {"air_temperature": 2.0}}}},
            ]
        }
    }

    points = list(iter_met_points(data))
    assert len(points) == 1
    assert points[0].utc_dt.tzinfo is not None
