from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from met_weather_service.core.config import settings


@dataclass(frozen=True)
class MetResponse:
    status_code: int
    data: dict[str, Any]


def _truncate_coord(value: float) -> float:
    return round(value, 4)


class MetClient:
    def __init__(self) -> None:
        if not settings.user_agent:
            raise RuntimeError("MET_USER_AGENT is not set (required by MET Norway ToS).")
        self._timeout = httpx.Timeout(
            settings.read_timeout_s,
            connect=settings.connect_timeout_s,
        )
        self._headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def fetch_locationforecast_compact(self, lat: float, lon: float) -> MetResponse:
        lat = _truncate_coord(lat)
        lon = _truncate_coord(lon)

        url = f"{settings.met_base_url}/compact"
        params = {"lat": lat, "lon": lon}

        with httpx.Client(headers=self._headers, timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)

        resp.raise_for_status()
        return MetResponse(status_code=resp.status_code, data=resp.json())
