from __future__ import annotations

import logging
import threading
import time

import httpx

from met_weather_service.core.config import get_settings
from met_weather_service.services.geocoder_client import GeocoderClient, GeoPlace
from met_weather_service.services.met_client import truncate_coord
from met_weather_service.services.rate_limiter import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)


class GeocoderRateLimitExceeded(Exception):
    pass


_cache_lock = threading.Lock()
_forward_cache: dict[tuple[str, int], tuple[float, list[GeoPlace]]] = {}
_reverse_cache: dict[tuple[float, float], tuple[float, GeoPlace | None]] = {}

_limiter: SlidingWindowRateLimiter | None = None
_limiter_cfg: tuple[int, float] | None = None


def clear_cache() -> None:
    with _cache_lock:
        _forward_cache.clear()
        _reverse_cache.clear()
        global _limiter, _limiter_cfg
        _limiter = None
        _limiter_cfg = None


def _ensure_limiter() -> tuple[int, float]:
    settings = get_settings()
    max_calls = int(settings.geocoder_rl_max_calls)
    period_s = float(settings.geocoder_rl_period_s)

    global _limiter, _limiter_cfg
    cfg = (max_calls, period_s)
    if _limiter is None or _limiter_cfg != cfg:
        if max_calls > 0 and period_s > 0:
            _limiter = SlidingWindowRateLimiter(max_calls=max_calls, period_s=period_s)
            _limiter_cfg = cfg
        else:
            _limiter = None
            _limiter_cfg = cfg

    return max_calls, period_s


def _check_rate_limit() -> None:
    max_calls, period_s = _ensure_limiter()
    if _limiter is not None and not _limiter.allow():
        logger.warning("Geocoder rate limit exceeded max_calls=%s period_s=%s", max_calls, period_s)
        raise GeocoderRateLimitExceeded("Geocoder rate limit exceeded")


def forward_geocode(query: str, *, limit: int = 5) -> list[GeoPlace]:
    settings = get_settings()
    ttl_s = float(settings.geocoder_cache_ttl_s)

    q_norm = " ".join(query.strip().split()).lower()
    key = (q_norm, int(limit))
    now = time.time()

    with _cache_lock:
        cached = _forward_cache.get(key)
        if cached and now < cached[0]:
            logger.info("Geocoder forward cache hit key=%s", key)
            return cached[1]

    _check_rate_limit()

    try:
        places = GeocoderClient().forward(query, limit=limit)
    except (httpx.HTTPError, ValueError):
        logger.exception("Geocoder forward upstream failure q=%s", q_norm)
        raise

    with _cache_lock:
        _forward_cache[key] = (now + ttl_s, places)

    return places


def reverse_geocode(lat: float, lon: float) -> GeoPlace | None:
    settings = get_settings()
    ttl_s = float(settings.geocoder_cache_ttl_s)

    lat_t = truncate_coord(lat)
    lon_t = truncate_coord(lon)
    key = (lat_t, lon_t)
    now = time.time()

    with _cache_lock:
        cached = _reverse_cache.get(key)
        if cached and now < cached[0]:
            logger.info("Geocoder reverse cache hit key=%s", key)
            return cached[1]

    _check_rate_limit()

    try:
        place = GeocoderClient().reverse(lat_t, lon_t)
    except (httpx.HTTPError, ValueError):
        logger.exception("Geocoder reverse upstream failure lat=%s lon=%s", lat_t, lon_t)
        raise

    with _cache_lock:
        _reverse_cache[key] = (now + ttl_s, place)

    return place
