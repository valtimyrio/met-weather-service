# met-weather-service

A small Python service (API) that will provide daily temperature in Belgrade around 14:00 using MET Norway (yr.no) API.

## Run locally

The `MET_USER_AGENT` environment variable **must** be set (required by MET Norway ToS).

Example:

```text
met-weather-service/0.1 (github.com/user/met-weather-service, mail@example.com)
```

Install dependencies:

```bash
pip install -e .
```

## Start server:

```bash
uvicorn met_weather_service.main:app
```

## Check health:

```bash 
curl http://127.0.0.1:8000/health
```

## Check MET connectivity

```bash
curl http://127.0.0.1:8000/health/met
```
