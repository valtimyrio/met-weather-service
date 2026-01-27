from __future__ import annotations

import logging
import re
from datetime import time
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from met_weather_service.core.config import get_settings
from met_weather_service.services.forecast import DailyTemperatureSelector
from met_weather_service.services.met_client import truncate_coord
from met_weather_service.services.met_gateway import get_locationforecast_compact, MetRateLimitExceeded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["forecast"])


class LocationInfo(BaseModel):
    lat: float = Field(
        ...,
        description="Latitude used for the upstream MET request (truncated to 4 decimals).",
        json_schema_extra={"example": 44.8125},
    )
    lon: float = Field(
        ...,
        description="Longitude used for the upstream MET request (truncated to 4 decimals).",
        json_schema_extra={"example": 20.4612},
    )

    timezone: str = Field(
        ...,
        description="IANA timezone used for local time selection.",
        json_schema_extra={"example": "Europe/Belgrade"},
    )

    target_time: str = Field(
        ...,
        description="Requested local time in HH:MM format.",
        json_schema_extra={"example": "14:00"},
    )


class DayForecast(BaseModel):
    date: str = Field(
        ...,
        description="Local date (YYYY-MM-DD) in the selected timezone.",
        json_schema_extra={"example": "2026-01-26"},
    )
    time: str = Field(
        ...,
        description="Selected local datetime (ISO8601) in the selected timezone.",
        json_schema_extra={"example": "2026-01-26T14:00:00+01:00"},
    )
    temperature_c: float = Field(
        ...,
        description="Air temperature in Celsius.",
        json_schema_extra={"example": 2.0},
    )


class ForecastResponse(BaseModel):
    location: LocationInfo
    days: list[DayForecast]


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


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Daily temperature near a local time",
    description=(
            "Fetches MET forecast timeseries and selects, for each local date, "
            "the point nearest to the requested local time. "
            "Coordinates are truncated to 4 decimals as required by MET ToS."
    ),
    responses={
        422: {"description": "Validation error (invalid timezone, time format or coordinates)."},
        500: {"description": "Service misconfiguration (e.g. MET_USER_AGENT missing)."},
        502: {"description": "Upstream MET/network error."},
        429: {"description": "Too many requests (service-side rate limiting to protect MET)."},
    },
)
def forecast(
        lat: Annotated[
            float | None,
            Query(
                ge=-90,
                le=90,
                description="Latitude in range [-90, 90]. Defaults to Belgrade.",
                examples=[44.81259],
            ),
        ] = None,
        lon: Annotated[
            float | None,
            Query(
                ge=-180,
                le=180,
                description="Longitude in range [-180, 180]. Defaults to Belgrade.",
                examples=[20.46129],
            ),
        ] = None,
        tz: Annotated[
            str,
            Query(
                description="IANA timezone name.",
                examples=["Europe/Belgrade"],
            ),
        ] = "Europe/Belgrade",
        at: Annotated[
            str,
            Query(
                description="Target local time in strict HH:MM format.",
                examples=["14:00"],
            ),
        ] = "14:00",
) -> ForecastResponse:
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
        data = get_locationforecast_compact(used_lat, used_lon)

    except RuntimeError as exc:
        logger.exception("Service misconfiguration in /v1/forecast")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    except MetRateLimitExceeded as exc:
        logger.warning("Rate limit exceeded in /v1/forecast")
        raise HTTPException(status_code=429, detail="Too many requests") from exc

    except (httpx.HTTPError, ValueError) as exc:
        logger.exception(
            "MET upstream failure in /v1/forecast "
            "lat=%s lon=%s used_lat=%s used_lon=%s tz=%s at=%s",
            lat,
            lon,
            used_lat,
            used_lon,
            tz_name,
            at,
        )
        raise HTTPException(status_code=502, detail="MET upstream error") from exc

    except Exception:
        logger.exception("Unexpected error in /v1/forecast")
        raise

    selector = DailyTemperatureSelector(
        tz_name=tz_name,
        target_time=target_time,
    )
    days = selector.select_from_met_response(data)

    return ForecastResponse(
        location=LocationInfo(
            lat=used_lat,
            lon=used_lon,
            timezone=tz_name,
            target_time=at,
        ),
        days=[
            DayForecast(
                date=p.date,
                time=p.time,
                temperature_c=p.temperature_c,
            )
            for p in days
        ],
    )
