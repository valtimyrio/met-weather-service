from fastapi import FastAPI

from met_weather_service.api.health import router as health_router

app = FastAPI(
    title="MET Weather Service",
    version="0.1.0",
    description="Weather proxy service based on MET Norway (yr.no) API.",
)

app.include_router(health_router)
