import logging

import httpx
from fastapi import APIRouter, HTTPException

from met_weather_service.core.config import get_settings
from met_weather_service.services.met_client import MetClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["service"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/met")
def health_met() -> dict[str, str]:
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

        return {
            "status": "ok",
            "met": "ok",
            "updated_at": str(updated_at),
        }

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
