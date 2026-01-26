from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetPoint:
    utc_dt: datetime
    temperature_c: float


@dataclass(frozen=True)
class ForecastPoint:
    date: str  # YYYY-MM-DD in selected timezone
    time: str  # ISO8601 in selected timezone
    temperature_c: float


def parse_met_iso_datetime(ts: str) -> datetime:
    # MET sends "...Z" (UTC), format is required
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    return dt


def iter_met_points(data: dict[str, Any]) -> Iterator[MetPoint]:
    timeseries = data.get("properties", {}).get("timeseries", [])
    if not isinstance(timeseries, list):
        logger.warning("MET response has no valid timeseries array")
        return

    for idx, item in enumerate(timeseries):
        try:
            ts_str = item["time"]
            utc_dt = parse_met_iso_datetime(ts_str)

            temp = item["data"]["instant"]["details"]["air_temperature"]
            yield MetPoint(utc_dt=utc_dt, temperature_c=float(temp))

        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Skipping malformed MET timeseries entry",
                extra={
                    "index": idx,
                    "error": type(exc).__name__,
                    "item_keys": list(item.keys()) if isinstance(item, dict) else None,
                },
            )
            continue


def target_datetime_for_day(local_dt: datetime, tz: ZoneInfo, target_time: time) -> datetime:
    # target_time - local time, 14:00 as example, at the same timezone
    return datetime.combine(local_dt.date(), target_time, tzinfo=tz)


def distance_to_target(local_dt: datetime, tz: ZoneInfo, target_time: time) -> timedelta:
    target_dt = target_datetime_for_day(local_dt, tz, target_time)
    return abs(local_dt - target_dt)


def select_daily_temperature_near_time(
        points: Iterable[MetPoint],
        tz_name: str,
        target_time: time,
) -> list[ForecastPoint]:
    tz = ZoneInfo(tz_name)

    best: dict[str, tuple[timedelta, datetime, float]] = {}

    for p in points:
        local_dt = p.utc_dt.astimezone(tz)
        day_key = local_dt.date().isoformat()
        delta = distance_to_target(local_dt, tz, target_time)

        prev = best.get(day_key)
        if prev is None or delta < prev[0]:
            best[day_key] = (delta, local_dt, p.temperature_c)

    out: list[ForecastPoint] = []
    for day_key in sorted(best.keys()):
        _, local_dt, temp = best[day_key]
        out.append(
            ForecastPoint(
                date=day_key,
                time=local_dt.isoformat(),
                temperature_c=temp,
            )
        )

    logger.info(
        "Selected daily points: days=%d tz=%s target_time=%s",
        len(out),
        tz_name,
        target_time.isoformat(timespec="minutes"),
    )

    return out


@dataclass(frozen=True)
class DailyTemperatureSelector:
    tz_name: str
    target_time: time

    def select_from_met_response(self, data: dict[str, Any]) -> list[ForecastPoint]:
        points = iter_met_points(data)
        return select_daily_temperature_near_time(points, self.tz_name, self.target_time)
