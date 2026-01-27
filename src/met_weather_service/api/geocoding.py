from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from met_weather_service.services.geocoder_gateway import (
    GeocoderRateLimitExceeded,
    forward_geocode,
    reverse_geocode,
)
from met_weather_service.services.met_client import truncate_coord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["geocoding"])


class GeocodePlace(BaseModel):
    display_name: str = Field(..., json_schema_extra={"example": "Belgrade, City of Belgrade, Central Serbia, Serbia"})
    lat: float = Field(..., json_schema_extra={"example": 44.8125})
    lon: float = Field(..., json_schema_extra={"example": 20.4612})
    country: str | None = Field(None, json_schema_extra={"example": "Serbia"})
    city: str | None = Field(None, json_schema_extra={"example": "Belgrade"})
    state: str | None = Field(None, json_schema_extra={"example": "Central Serbia"})


class GeocodeResponse(BaseModel):
    query: str
    results: list[GeocodePlace]


class ReverseResponse(BaseModel):
    lat: float
    lon: float
    place: GeocodePlace | None


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Forward geocoding (place name -> coordinates)",
    responses={
        422: {"description": "Validation error."},
        429: {"description": "Too many requests (geocoder rate limiting)."},
        500: {"description": "Service misconfiguration (GEOCODER_USER_AGENT missing)."},
        502: {"description": "Upstream geocoder/network error."},
    },
)
def geocode(
        q: Annotated[str, Query(min_length=2, max_length=200, description="Place name query")],
        limit: Annotated[int, Query(ge=1, le=5, description="Max number of results")] = 5,
) -> GeocodeResponse:
    logger.info("Request /v1/geocode q=%s limit=%s", q, limit)

    try:
        places = forward_geocode(q, limit=limit)
    except GeocoderRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="Too many requests") from exc
    except RuntimeError as exc:
        logger.exception("Geocoder misconfiguration")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Geocoder upstream error") from exc

    return GeocodeResponse(
        query=q,
        results=[
            GeocodePlace(
                display_name=p.display_name,
                lat=truncate_coord(p.lat),
                lon=truncate_coord(p.lon),
                country=p.country,
                city=p.city,
                state=p.state,
            )
            for p in places
        ],
    )


@router.get(
    "/reverse",
    response_model=ReverseResponse,
    summary="Reverse geocoding (coordinates -> place name)",
    responses={
        422: {"description": "Validation error."},
        429: {"description": "Too many requests (geocoder rate limiting)."},
        500: {"description": "Service misconfiguration (GEOCODER_USER_AGENT missing)."},
        502: {"description": "Upstream geocoder/network error."},
    },
)
def reverse(
        lat: Annotated[float, Query(ge=-90, le=90)],
        lon: Annotated[float, Query(ge=-180, le=180)],
) -> ReverseResponse:
    used_lat = truncate_coord(lat)
    used_lon = truncate_coord(lon)

    logger.info("Request /v1/reverse lat=%s lon=%s used_lat=%s used_lon=%s", lat, lon, used_lat, used_lon)

    try:
        place = reverse_geocode(used_lat, used_lon)
    except GeocoderRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="Too many requests") from exc
    except RuntimeError as exc:
        logger.exception("Geocoder misconfiguration")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Geocoder upstream error") from exc

    return ReverseResponse(
        lat=used_lat,
        lon=used_lon,
        place=(
            GeocodePlace(
                display_name=place.display_name,
                lat=truncate_coord(place.lat),
                lon=truncate_coord(place.lon),
                country=place.country,
                city=place.city,
                state=place.state,
            )
            if place
            else None
        ),
    )
