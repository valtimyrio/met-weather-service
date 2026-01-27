from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from met_weather_service.core.config import get_settings
from met_weather_service.services.met_client import MetClient, truncate_coord

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    data: dict[str, Any]
    last_modified: str | None
    expires_at: float


_cache_lock = threading.Lock()
_cache: dict[tuple[float, float], _CacheEntry] = {}


def clear_cache() -> None:
    """
    Test helper. Clears in-memory cache.
    """
    with _cache_lock:
        _cache.clear()


def get_locationforecast_compact(lat: float, lon: float) -> dict[str, Any]:
    """
    Return MET locationforecast compact payload.

    Strategy:
    - Coordinates are truncated to 4 decimals (ToS).
    - In-memory TTL cache per (lat_trunc, lon_trunc).
    - When TTL expires and we have Last-Modified, revalidate with If-Modified-Since:
        - 200: update cache with new body
        - 304: refresh TTL and keep cached body
    """
    settings = get_settings()

    if not settings.user_agent:
        raise RuntimeError("MET_USER_AGENT is not set (required by MET Norway ToS).")

    ttl_s = float(settings.met_cache_ttl_s)

    lat_t = truncate_coord(lat)
    lon_t = truncate_coord(lon)
    key = (lat_t, lon_t)

    now = time.time()

    with _cache_lock:
        entry = _cache.get(key)
        if entry and now < entry.expires_at:
            logger.info("MET cache hit key=%s ttl_left_s=%.2f", key, entry.expires_at - now)
            return entry.data

    if_modified_since: str | None = None
    if entry:
        if_modified_since = entry.last_modified

    client = MetClient()
    resp = client.fetch_locationforecast_compact(lat_t, lon_t, if_modified_since=if_modified_since)

    # 304 Not Modified -> keep cached body, refresh TTL
    if resp.status_code == 304:
        if not entry:
            raise ValueError("MET returned 304 but no cached response is available")

        new_expires = now + ttl_s
        new_last_modified = resp.last_modified or entry.last_modified

        with _cache_lock:
            _cache[key] = _CacheEntry(
                data=entry.data,
                last_modified=new_last_modified,
                expires_at=new_expires,
            )

        logger.info("MET cache revalidated (304) key=%s new_ttl_s=%.2f", key, ttl_s)
        return entry.data

    # 200 OK (or other 2xx) -> must have JSON body
    if resp.data is None:
        raise ValueError("MET returned response without JSON body")

    new_entry = _CacheEntry(
        data=resp.data,
        last_modified=resp.last_modified,
        expires_at=now + ttl_s,
    )

    with _cache_lock:
        _cache[key] = new_entry

    logger.info("MET cache stored key=%s ttl_s=%.2f last_modified=%s", key, ttl_s, resp.last_modified)
    return resp.data
