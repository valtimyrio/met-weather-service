from fastapi import FastAPI

from met_weather_service.api.forecast import router as forecast_router
from met_weather_service.api.geocoding import router as geocoding_router
from met_weather_service.api.health import router as health_router
from met_weather_service.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="MET Weather Service",
    version="0.1.0",
    description="Weather proxy service based on MET Norway (yr.no) API.",
)

app.include_router(health_router)
app.include_router(forecast_router)
app.include_router(geocoding_router)
