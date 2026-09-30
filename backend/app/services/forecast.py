import logging
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.providers.base import IngestionContext
from app.providers.mock_provider import MockWeatherProvider
from app.services.provider_factory import build_forecast_provider
from app.storage.repository import WeatherRepository

logger = logging.getLogger(__name__)


def forecast_key(lat: float, lon: float) -> str:
    return f"forecast:{lat:.4f}:{lon:.4f}"


class ForecastService:
    def __init__(self, repo: WeatherRepository, settings: Settings):
        self.repo = repo
        self.settings = settings

    def get(self, context: IngestionContext):
        lat, lon = round(context.lat, 4), round(context.lon, 4)
        rows = self.repo.list_forecast(lat, lon)
        now = datetime.now(timezone.utc)
        created = rows[0].created_at if rows else None
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and created > now - timedelta(minutes=self.settings.refresh_interval_minutes):
            return rows
        key = forecast_key(lat, lon)
        try:
            points = build_forecast_provider(self.settings).fetch_forecast(context)
            if not points:
                raise ValueError("empty forecast")
            self.repo.replace_forecast(points)
            self.repo.update_refresh_status(key)
        except Exception:
            self.repo.db.rollback()
            logger.exception("Location forecast refresh failed")
            if self.settings.fallback_to_mock_on_failure:
                points = MockWeatherProvider().fetch_forecast(context)
                self.repo.replace_forecast(points)
                self.repo.update_refresh_status(key, error="预报源异常，当前曲线为演示数据")
            else:
                self.repo.update_refresh_status(key, error="预报源暂不可用，保留该坐标已有数据")
        return self.repo.list_forecast(lat, lon)
