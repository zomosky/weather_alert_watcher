from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import Settings
from app.models import ForecastPoint, WarningRecord
from app.providers.base import IngestionContext


class QWeatherProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _require_key(self) -> str:
        if not self.settings.qweather_api_key:
            raise RuntimeError("QWeather API key is required but missing")
        return self.settings.qweather_api_key

    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        key = self._require_key()
        params = {
            "location": f"{context.lon},{context.lat}",
            "lang": "zh",
            "key": key,
        }
        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.get(f"{self.settings.qweather_api_base.rstrip('/')}/warning/now", params=params)
            response.raise_for_status()
            payload = response.json()

        warnings = payload.get("warning", [])
        rows: list[WarningRecord] = []
        for item in warnings:
            issue_time = _parse_time(item.get("pubTime"))
            rows.append(
                WarningRecord(
                    source="QWeather",
                    title=item.get("title", "气象预警"),
                    level=item.get("severityColor", "未知"),
                    hazard_type=item.get("typeName", "综合风险"),
                    province=context.province,
                    issue_time=issue_time,
                    expires_at=issue_time + timedelta(hours=12),
                    detail_url=item.get("text", "https://dev.qweather.com"),
                    summary=item.get("text", ""),
                    confidence=1.0,
                )
            )
        return rows

    def fetch_forecast(self, context: IngestionContext) -> list[ForecastPoint]:
        key = self._require_key()
        params = {
            "location": f"{context.lon},{context.lat}",
            "lang": "zh",
            "key": key,
        }
        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.get(f"{self.settings.qweather_api_base.rstrip('/')}/weather/7d", params=params)
            response.raise_for_status()
            payload = response.json()

        daily = payload.get("daily", [])
        rows: list[ForecastPoint] = []
        for day in daily:
            date_text = day.get("fxDate")
            if not date_text:
                continue
            base_dt = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
            for hour_offset in (0, 6, 12, 18):
                rows.append(
                    ForecastPoint(
                        lat=round(context.lat, 4),
                        lon=round(context.lon, 4),
                        location_label=context.label,
                        province=context.province,
                        forecast_time=base_dt + timedelta(hours=hour_offset),
                        temperature_c=float(day.get("tempMax", 0) if hour_offset < 12 else day.get("tempMin", 0)),
                        humidity_pct=float(day.get("humidity", 0)),
                        source="QWeather",
                    )
                )
        return rows


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
