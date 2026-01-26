# src/met_weather_service/services/met_client.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from met_weather_service.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetResponse:
    status_code: int
    data: dict[str, Any]


def _truncate_coord(value: float) -> float:
    return round(value, 4)


class MetClient:
    def __init__(self) -> None:
        s = get_settings()
        if not s.user_agent:
            raise RuntimeError("MET_USER_AGENT is not set (required by MET Norway ToS).")

        self._base_url = s.met_base_url
        self._timeout = httpx.Timeout(s.read_timeout_s, connect=s.connect_timeout_s)
        self._headers = {
            "User-Agent": s.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def fetch_locationforecast_compact(self, lat: float, lon: float) -> MetResponse:
        lat = _truncate_coord(lat)
        lon = _truncate_coord(lon)

        url = f"{self._base_url}/compact"
        params = {"lat": lat, "lon": lon}

        logger.info("MET request: %s params=%s", url, params)

        with httpx.Client(headers=self._headers, timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)

        logger.info("MET response: status=%s", resp.status_code)

        if resp.status_code == 203:
            logger.warning("MET response is deprecated (203). Consider updating API version.")

        resp.raise_for_status()
        return MetResponse(status_code=resp.status_code, data=resp.json())
