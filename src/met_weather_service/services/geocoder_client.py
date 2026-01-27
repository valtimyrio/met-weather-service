from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from met_weather_service.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeoPlace:
    display_name: str
    lat: float
    lon: float
    country: str | None
    city: str | None
    state: str | None
    raw: dict[str, Any]


def _pick_city(address: dict[str, Any]) -> str | None:
    # Nominatim sometimes uses different keys
    for key in ("city", "town", "village", "municipality", "hamlet", "county"):
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


class GeocoderClient:
    """
    Thin client for a geocoding provider (default: Nominatim).
    """

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.geocoder_user_agent:
            raise RuntimeError("GEOCODER_USER_AGENT is not set (required by geocoding provider policies).")

        self._base_url = settings.geocoder_base_url.rstrip("/")
        self._timeout = httpx.Timeout(
            settings.read_timeout_s,
            connect=settings.connect_timeout_s,
        )
        self._headers = {
            "User-Agent": settings.geocoder_user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def forward(self, query: str, *, limit: int = 5) -> list[GeoPlace]:
        url = f"{self._base_url}/search"
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": str(limit),
            "addressdetails": "1",
        }

        logger.info("Geocoder forward request: %s params=%s", url, params)

        with httpx.Client(headers=self._headers, timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)

        logger.info("Geocoder forward response: status=%s", resp.status_code)
        resp.raise_for_status()

        payload = resp.json()
        if not isinstance(payload, list):
            raise ValueError("Geocoder returned unexpected payload type")

        out: list[GeoPlace] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            display_name = item.get("display_name")
            lat = item.get("lat")
            lon = item.get("lon")
            address = item.get("address") if isinstance(item.get("address"), dict) else {}
            if not isinstance(display_name, str):
                continue
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (TypeError, ValueError):
                continue

            country = address.get("country") if isinstance(address.get("country"), str) else None
            state = address.get("state") if isinstance(address.get("state"), str) else None
            city = _pick_city(address)

            out.append(
                GeoPlace(
                    display_name=display_name,
                    lat=lat_f,
                    lon=lon_f,
                    country=country,
                    city=city,
                    state=state,
                    raw=item,
                )
            )

        return out

    def reverse(self, lat: float, lon: float) -> GeoPlace | None:
        url = f"{self._base_url}/reverse"
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "format": "jsonv2",
            "addressdetails": "1",
        }

        logger.info("Geocoder reverse request: %s params=%s", url, params)

        with httpx.Client(headers=self._headers, timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)

        logger.info("Geocoder reverse response: status=%s", resp.status_code)
        resp.raise_for_status()

        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("Geocoder returned unexpected payload type")

        display_name = payload.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            return None

        address = payload.get("address") if isinstance(payload.get("address"), dict) else {}
        country = address.get("country") if isinstance(address.get("country"), str) else None
        state = address.get("state") if isinstance(address.get("state"), str) else None
        city = _pick_city(address)

        lat_s = payload.get("lat")
        lon_s = payload.get("lon")
        try:
            lat_f = float(lat_s) if lat_s is not None else float(lat)
            lon_f = float(lon_s) if lon_s is not None else float(lon)
        except (TypeError, ValueError):
            lat_f = float(lat)
            lon_f = float(lon)

        return GeoPlace(
            display_name=display_name,
            lat=lat_f,
            lon=lon_f,
            country=country,
            city=city,
            state=state,
            raw=payload,
        )
