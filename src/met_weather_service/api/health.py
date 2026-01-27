import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from met_weather_service.core.config import get_settings
from met_weather_service.services.met_client import MetClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["service"])


class HealthResponse(BaseModel):
    status: str = Field(
        ...,
        json_schema_extra={"example": "ok"},
    )


class HealthMetResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    met: str = Field(..., json_schema_extra={"example": "ok"})
    updated_at: str = Field(
        ...,
        description="Value of properties.meta.updated_at from MET response.",
        json_schema_extra={"example": "2026-01-26T17:15:58Z"},
    )


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/met",
    response_model=HealthMetResponse,
    summary="Upstream MET health",
    description="Checks connectivity to MET Norway Locationforecast API.",
    responses={
        500: {"description": "Service misconfiguration (e.g. MET_USER_AGENT missing)."},
        502: {"description": "Upstream MET/network error."},
    },
)
def health_met() -> HealthMetResponse:
    settings = get_settings()

    try:
        client = MetClient()
        data = client.fetch_locationforecast_compact(
            settings.default_lat,
            settings.default_lon,
        ).data

        updated_at = (
            data.get("properties", {})
            .get("meta", {})
            .get("updated_at", "")
        )

        return HealthMetResponse(
            status="ok",
            met="ok",
            updated_at=str(updated_at),
        )


    except RuntimeError as exc:
        # service misconfiguration (e.g. MET_USER_AGENT missing)
        logger.exception("Service misconfiguration")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    except httpx.HTTPError as exc:
        # network / upstream HTTP errors
        logger.exception("MET network/http error")
        raise HTTPException(
            status_code=502,
            detail=f"MET upstream error: {type(exc).__name__}",
        ) from exc

    except Exception as exc:
        # anything unexpected
        logger.exception("Unexpected MET error")
        raise HTTPException(
            status_code=502,
            detail=f"MET upstream error: {type(exc).__name__}",
        ) from exc
