# met-weather-service

A small FastAPI service that returns daily air temperature for a location "around" a requested local time (default 14:00).
It uses MET Norway (yr.no) Locationforecast API as the upstream data source.

The service also provides forward and reverse geocoding (default provider - Nominatim/OpenStreetMap) and can optionally enrich forecast responses with a human-readable place name.

Key behavior
- For each local date, the service selects the forecast point with the minimal absolute time difference to the requested local time.
- If MET does not provide a point exactly at the requested time, the nearest available point is used.
- Coordinates sent to MET are truncated to 4 decimal places (MET ToS requirement). The same truncated coordinates are returned in the API response.
- Upstream protection (per process):
  - In-memory cache with TTL for MET responses
  - Conditional requests to MET via If-Modified-Since (based on Last-Modified)
  - Rate limiting for MET upstream calls
  - In-memory cache with TTL for geocoder responses
  - Rate limiting for geocoder upstream calls

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
Checks connectivity to MET for the default coordinates (Belgrade by default). Returns upstream `properties.meta.updated_at` if available.

Responses:
- 200 - MET reachable
- 429 - too many requests (service-side upstream rate limiting)
- 500 - service misconfiguration (for example `MET_USER_AGENT` missing)
- 502 - MET/network error

### GET /v1/forecast
Returns daily temperature points for the requested location.

Query params:
- `lat` (float, optional) - latitude in range [-90, 90]. Default: Belgrade latitude.
- `lon` (float, optional) - longitude in range [-180, 180]. Default: Belgrade longitude.
- `tz` (str, optional) - IANA timezone name. Default: `Europe/Belgrade`.
- `at` (str, optional) - local target time in strict `HH:MM`. Default: `14:00`.
- `include_place` (bool, optional) - if true, enrich response with reverse-geocoded place name. Default: false.

Example:
```bash
curl "http://127.0.0.1:8000/v1/forecast?lat=44.81259&lon=20.46129&tz=Europe/Belgrade&at=14:00&include_place=true"
```

Response (200):
```json
{
  "location": {
    "lat": 44.8125,
    "lon": 20.4612,
    "timezone": "Europe/Belgrade",
    "target_time": "14:00",
    "place_name": "Belgrade, City of Belgrade, Central Serbia, Serbia",
    "country": "Serbia",
    "city": "Belgrade",
    "geocoder": "nominatim"
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
- 429 - too many requests (service-side rate limiting for upstream calls)
- 500 - service misconfiguration (for example `MET_USER_AGENT` missing)
- 502 - upstream/network error

Note:
- `include_place=true` is best-effort. If the geocoder is unavailable or rate-limited, the forecast still returns 200 but without place fields.

### GET /v1/geocode
Forward geocoding (place name -> coordinates).

Query params:
- `q` (str, required) - place name query (min 2 chars)
- `limit` (int, optional) - max number of results (1..5). Default: 5.

Example:
```bash
curl "http://127.0.0.1:8000/v1/geocode?q=Belgrade&limit=1"
```

Responses:
- 200 - ok
- 429 - too many requests (geocoder rate limiting)
- 500 - service misconfiguration (for example `GEOCODER_USER_AGENT` missing)
- 502 - geocoder/network error

### GET /v1/reverse
Reverse geocoding (coordinates -> place name).

Query params:
- `lat` (float, required) - latitude in range [-90, 90]
- `lon` (float, required) - longitude in range [-180, 180]

Example:
```bash
curl "http://127.0.0.1:8000/v1/reverse?lat=44.8125&lon=20.4612"
```

Responses:
- 200 - ok
- 429 - too many requests (geocoder rate limiting)
- 500 - service misconfiguration (for example `GEOCODER_USER_AGENT` missing)
- 502 - geocoder/network error

Note:
- The geocoding provider may localize place names depending on request defaults. This service currently does not force a specific language.

## Configuration

Environment variables:

MET (yr.no)
- `MET_USER_AGENT` (required) - required by MET Norway ToS. Must identify the application.
  Example:
  `met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)`
- `DEFAULT_LAT` (optional, default 44.8125)
- `DEFAULT_LON` (optional, default 20.4612)
- `MET_BASE_URL` (optional, default https://api.met.no/weatherapi/locationforecast/2.0)

HTTP
- `HTTP_CONNECT_TIMEOUT_S` (optional, default 5.0)
- `HTTP_READ_TIMEOUT_S` (optional, default 10.0)

Logging
- `LOG_LEVEL` (optional, default INFO)

Caching and rate limiting (per process)
- `MET_CACHE_TTL_S` (optional, default 300)
- `MET_RL_MAX_CALLS` (optional, default 60)
- `MET_RL_PERIOD_S` (optional, default 60)

Geocoding (default provider - Nominatim/OpenStreetMap)
- `GEOCODER_USER_AGENT` (required) - required by the geocoding provider policies.
  Example:
  `met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)`
- `GEOCODER_BASE_URL` (optional, default https://nominatim.openstreetmap.org)
- `GEOCODER_CACHE_TTL_S` (optional, default 86400)
- `GEOCODER_RL_MAX_CALLS` (optional, default 1)
- `GEOCODER_RL_PERIOD_S` (optional, default 1)

## Run locally (without Docker)

Install:
```bash
pip install -e .
```

Run:
```bash
export MET_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)"
export GEOCODER_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)"
uvicorn met_weather_service.main:app
```

## Run with Docker

Build:
```bash
docker build -t met-weather-service .
```

Run:
```bash
docker run --rm -p 8000:8000 \
  -e MET_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)" \
  -e GEOCODER_USER_AGENT="met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)" \
  met-weather-service
```

Run via compose:
- Set correct `MET_USER_AGENT` and `GEOCODER_USER_AGENT` in `docker-compose.yml`.
```bash
docker compose up --build
```

## Tests

```bash
pip install -e ".[test]"
pytest
```

## Notes on upstream compliance

MET Norway (yr.no)
- A non-empty `User-Agent` header is required and must identify the application.
- Latitude and longitude are truncated to 4 decimal places before calling MET.

Geocoding (Nominatim/OpenStreetMap by default)
- A non-empty `User-Agent` header is required.
- Public instances should be used responsibly. This service applies per-process caching and rate limiting.
