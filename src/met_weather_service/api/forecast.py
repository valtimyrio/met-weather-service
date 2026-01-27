from __future__ import annotations

import logging
import re
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query

from met_weather_service.core.config import get_settings
from met_weather_service.services.forecast import DailyTemperatureSelector
from met_weather_service.services.met_client import MetClient, truncate_coord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["forecast"])

_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")


def parse_hhmm(value: str) -> time:
    if not _HHMM_RE.match(value):
        raise ValueError("time must be in HH:MM format")

    hh_str, mm_str = value.split(":")
    hh = int(hh_str)
    mm = int(mm_str)
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("time must be in HH:MM format")

    return time(hour=hh, minute=mm)


def validate_timezone(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
        return tz_name
    except ZoneInfoNotFoundError:
        logger.warning("Invalid or unavailable timezone requested: %s", tz_name)
        raise ValueError("timezone not available")


@router.get("/forecast")
def forecast(
        lat: float | None = Query(default=None, ge=-90, le=90),
        lon: float | None = Query(default=None, ge=-180, le=180),
        tz: str = Query(default="Europe/Belgrade"),
        at: str = Query(default="14:00"),
) -> dict:
    logger.info("Request /v1/forecast lat=%s lon=%s tz=%s at=%s", lat, lon, tz, at)

    settings = get_settings()

    if lat is None:
        lat = settings.default_lat
    if lon is None:
        lon = settings.default_lon

    try:
        tz_name = validate_timezone(tz)
        target_time = parse_hhmm(at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    used_lat = truncate_coord(lat)
    used_lon = truncate_coord(lon)

    try:
        data = MetClient().fetch_locationforecast_compact(used_lat, used_lon).data
    except RuntimeError as exc:
        logger.exception("Service misconfiguration")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("MET upstream failure")
        raise HTTPException(
            status_code=502,
            detail=f"MET upstream error: {type(exc).__name__}",
        ) from exc

    selector = DailyTemperatureSelector(
        tz_name=tz_name,
        target_time=target_time,
    )
    days = selector.select_from_met_response(data)

    return {
        "location": {
            "lat": used_lat,
            "lon": used_lon,
            "timezone": tz_name,
            "target_time": at,
        },
        "days": [
            {
                "date": p.date,
                "time": p.time,
                "temperature_c": p.temperature_c,
            }
            for p in days
        ],
    }
