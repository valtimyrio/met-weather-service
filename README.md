# met-weather-service

A small FastAPI service that returns daily air temperature for a location "around" a requested local time (default 14:00).
It uses MET Norway (yr.no) Locationforecast API as the upstream data source.

Key behavior
- For each local date, the service selects the forecast point with the minimal absolute time difference to the requested local time.
- If MET does not provide a point exactly at the requested time, the nearest available point is used.
- Coordinates sent to MET are truncated to 4 decimal places (MET ToS requirement). The same truncated coordinates are returned in the API response.

## Upstream load protection (caching)

To avoid overloading MET (yr.no), the service uses an in-memory cache per (lat, lon) for MET `compact` responses.

- TTL cache: responses are cached for `MET_CACHE_TTL_S` seconds (default 300).
- Conditional requests: when TTL expires and the upstream provided `Last-Modified`, the service revalidates with `If-Modified-Since`.
  - If MET replies `304 Not Modified`, the cached body is reused and TTL is refreshed.


## API

Swagger UI is available at:
- /docs

### GET /health
Liveness probe.

Response (200):
```json
{"status":"ok"}
```

### GET /health/met
Checks connectivity to MET for the default coordinates (Belgrade by default). Returns upstream `updated_at` if available.

Responses:
- 200: MET reachable
- 500: service misconfiguration (for example `MET_USER_AGENT` missing)
- 502: MET/network error

### GET /v1/forecast
Returns daily temperature points for the requested location.

Query params:
- `lat` (float, optional) - Latitude in range [-90, 90]. Default: Belgrade latitude.
- `lon` (float, optional) - Longitude in range [-180, 180]. Default: Belgrade longitude.
- `tz` (str, optional) - IANA timezone name. Default: `Europe/Belgrade`.
- `at` (str, optional) - Local target time in strict `HH:MM`. Default: `14:00`.

Example:
```bash
curl "http://127.0.0.1:8000/v1/forecast?lat=44.81259&lon=20.46129&tz=Europe/Belgrade&at=14:00"
```

Response (200):
```json
{
  "location": {
    "lat": 44.8125,
    "lon": 20.4612,
    "timezone": "Europe/Belgrade",
    "target_time": "14:00"
  },
  "days": [
    {
      "date": "2026-01-26",
      "time": "2026-01-26T14:00:00+01:00",
      "temperature_c": 2.0
    }
  ]
}
```

Errors:
- 422 - validation error (invalid `tz`, invalid `at`, lat/lon out of range)
- 500 - service misconfiguration (for example `MET_USER_AGENT` missing)
- 502 - MET/network error

## Configuration

Environment variables:
- `MET_USER_AGENT` (required) - required by MET Norway ToS.
  Example:
  `met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)`
- `DEFAULT_LAT` (optional, default 44.8125)
- `DEFAULT_LON` (optional, default 20.4612)
- `MET_BASE_URL` (optional, default https://api.met.no/weatherapi/locationforecast/2.0)
- `HTTP_CONNECT_TIMEOUT_S` (optional, default 5.0)
- `HTTP_READ_TIMEOUT_S` (optional, default 10.0)
- `LOG_LEVEL` (optional, default INFO)
- `MET_CACHE_TTL_S` (optional, default 300) - in-memory cache TTL for MET responses (seconds)


## Run locally (without Docker)

Install:
```bash
pip install -e .
```

Run:
```bash
export MET_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)"
uvicorn met_weather_service.main:app
```

## Run with Docker

Build:
```bash
docker build -t met-weather-service .
```

Run:
```bash
docker run --rm -p 8000:8000   -e MET_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)"   met-weather-service
```

Run via compose:

Need to set correct MET_USER_AGENT variable in the docker-compose file first.
```bash
docker compose up --build
```

## Tests

```bash
pip install -e ".[test]"
pytest
```

## Notes on MET Norway ToS compliance

- A non-empty `User-Agent` header is required and must identify the application.
- The client sets `Accept-Encoding: gzip, deflate`.
- Latitude and longitude are truncated to 4 decimal places before calling MET.
- The service supports conditional requests (`If-Modified-Since`) based on `Last-Modified` header to reduce upstream load.

