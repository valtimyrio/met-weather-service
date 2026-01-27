import os
from dataclasses import dataclass
from functools import lru_cache


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value.strip() else default


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None and value.strip() else default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None and value.strip() else default


@dataclass(frozen=True)
class Settings:
    default_lat: float
    default_lon: float
    met_base_url: str
    user_agent: str
    connect_timeout_s: float
    read_timeout_s: float
    met_cache_ttl_s: float
    met_rl_max_calls: int
    met_rl_period_s: float
    geocoder_base_url: str
    geocoder_user_agent: str
    geocoder_cache_ttl_s: float
    geocoder_rl_max_calls: int
    geocoder_rl_period_s: float


@lru_cache
def get_settings() -> Settings:
    return Settings(
        default_lat=_get_env_float("DEFAULT_LAT", 44.8125),
        default_lon=_get_env_float("DEFAULT_LON", 20.4612),
        met_base_url=_get_env("MET_BASE_URL", "https://api.met.no/weatherapi/locationforecast/2.0"),
        user_agent=_get_env("MET_USER_AGENT", ""),
        connect_timeout_s=_get_env_float("HTTP_CONNECT_TIMEOUT_S", 5.0),
        read_timeout_s=_get_env_float("HTTP_READ_TIMEOUT_S", 10.0),
        met_cache_ttl_s=_get_env_float("MET_CACHE_TTL_S", 300.0),
        met_rl_max_calls=int(_get_env_float("MET_RL_MAX_CALLS", 60.0)),
        met_rl_period_s=_get_env_float("MET_RL_PERIOD_S", 60.0),
        geocoder_base_url=_get_env("GEOCODER_BASE_URL", "https://nominatim.openstreetmap.org"),
        geocoder_user_agent=_get_env("GEOCODER_USER_AGENT", _get_env("MET_USER_AGENT", "")),
        geocoder_cache_ttl_s=_get_env_float("GEOCODER_CACHE_TTL_S", 86_400.0),
        geocoder_rl_max_calls=_get_env_int("GEOCODER_RL_MAX_CALLS", 1),
        geocoder_rl_period_s=_get_env_float("GEOCODER_RL_PERIOD_S", 1.0),

    )
