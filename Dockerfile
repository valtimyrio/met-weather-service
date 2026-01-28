# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends tzdata ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY src/ /app/src/

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir .

ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA


RUN useradd -r -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-lc", "test -n \"${MET_USER_AGENT}\" || (echo 'MET_USER_AGENT is required' && exit 1); uvicorn met_weather_service.main:app --host 0.0.0.0 --port 8000"]
