from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from dateutil.parser import isoparse

from app.core.config import Settings
from app.models import ForecastPoint
from app.providers.base import IngestionContext


class OpenMeteoForecastProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch_forecast(self, context: IngestionContext) -> list[ForecastPoint]:
        params = {
            "latitude": context.lat,
            "longitude": context.lon,
            "hourly": "temperature_2m,relative_humidity_2m",
            "forecast_days": 7,
            "timezone": "Asia/Shanghai",
        }

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.get(f"{self.settings.openmeteo_api_base.rstrip('/')}/forecast", params=params)
            response.raise_for_status()
            payload = response.json()

        hourly = payload.get("hourly", {})
        times: list[str] = hourly.get("time", [])
        temps: list[float] = hourly.get("temperature_2m", [])
        humidity: list[float] = hourly.get("relative_humidity_2m", [])

        rows: list[ForecastPoint] = []
        for idx, t in enumerate(times):
            if idx % 3 != 0:
                continue
            if idx >= len(temps) or idx >= len(humidity):
                break
            dt = isoparse(t)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            rows.append(
                ForecastPoint(
                    lat=round(context.lat, 4),
                    lon=round(context.lon, 4),
                    location_label=context.label,
                    province=context.province,
                    forecast_time=dt,
                    temperature_c=float(temps[idx]),
                    humidity_pct=float(humidity[idx]),
                    source="OpenMeteo",
                    created_at=datetime.utcnow(),
                )
            )

        return rows
