import os
from dataclasses import dataclass

def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value.strip() else default

def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None and value.strip() else default

def _get_env_timeout(name: str, default: float) -> float:
    return _get_env_float(name, default)

@dataclass(frozen=True)
class Settings:
    default_lat: float = _get_env_float("DEFAULT_LAT", 44.8125)
    default_lon: float = _get_env_float("DEFAULT_LON", 20.4612)

    met_base_url: str = _get_env("MET_BASE_URL", "https://api.met.no/weatherapi/locationforecast/2.0")

    # Require explicit UA in env for public repos
    user_agent: str = _get_env("MET_USER_AGENT", "")

    connect_timeout_s: float = _get_env_timeout("HTTP_CONNECT_TIMEOUT_S", 5.0)
    read_timeout_s: float = _get_env_timeout("HTTP_READ_TIMEOUT_S", 10.0)

settings = Settings()
