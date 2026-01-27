from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import httpx

from met_weather_service.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetResponse:
    status_code: int
    data: dict[str, Any] | None
    last_modified: str | None


def truncate_coord(value: float) -> float:
    """
    Truncate coordinate to max 4 decimal places as required by MET ToS.
    """
    return math.trunc(value * 10_000) / 10_000


class MetClient:
    def __init__(self) -> None:
        settings = get_settings()

        if not settings.user_agent:
            raise RuntimeError("MET_USER_AGENT is not set (required by MET Norway ToS).")

        self._base_url = settings.met_base_url
        self._timeout = httpx.Timeout(
            settings.read_timeout_s,
            connect=settings.connect_timeout_s,
        )
        self._headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def fetch_locationforecast_compact(
            self,
            lat: float,
            lon: float,
            *,
            if_modified_since: str | None = None,
    ) -> MetResponse:
        lat = truncate_coord(lat)
        lon = truncate_coord(lon)

        url = f"{self._base_url}/compact"
        params = {"lat": lat, "lon": lon}

        headers = dict(self._headers)
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since

        logger.info(
            "MET request: %s params=%s if_modified_since=%s",
            url,
            params,
            if_modified_since,
        )

        with httpx.Client(
                headers=headers,
                timeout=self._timeout,
                follow_redirects=True,
        ) as client:
            resp = client.get(url, params=params)

        logger.info("MET response: status=%s", resp.status_code)

        if resp.status_code == 203:
            logger.warning("MET response is deprecated (203). Consider updating API version.")

        # 304 means "no body, use cached representation"
        if resp.status_code == 304:
            return MetResponse(
                status_code=304,
                data=None,
                last_modified=resp.headers.get("Last-Modified"),
            )

        resp.raise_for_status()

        payload = resp.json()
        return MetResponse(
            status_code=resp.status_code,
            data=payload,
            last_modified=resp.headers.get("Last-Modified"),
        )
