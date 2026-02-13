from dataclasses import dataclass
import logging

from app.core.config import Settings, get_settings
from app.providers.base import IngestionContext
from app.providers.mock_provider import MockWeatherProvider
from app.services.ai_extractor import AiExtractor
from app.services.provider_factory import build_forecast_provider, build_warning_provider
from app.storage.repository import WeatherRepository

logger = logging.getLogger(__name__)


@dataclass
class IngestionInput:
    lat: float
    lon: float
    province: str
    label: str


class IngestionService:
    def __init__(self, repository: WeatherRepository, settings: Settings | None = None):
        self.repository = repository
        self.settings = settings or get_settings()
        self.ai_extractor = AiExtractor(self.settings)
        self.warning_provider = build_warning_provider(self.settings, self.ai_extractor)
        self.forecast_provider = build_forecast_provider(self.settings)
        self.fallback_provider = MockWeatherProvider()

    def refresh(self, payload: IngestionInput) -> None:
        context = IngestionContext(
            lat=payload.lat,
            lon=payload.lon,
            province=payload.province,
            label=payload.label,
        )
        if self.settings.warning_provider.lower() == "mock" or self.settings.forecast_provider.lower() == "mock":
            logger.info(
                "Ingestion running in demo mode (warning_provider=%s, forecast_provider=%s)",
                self.settings.warning_provider,
                self.settings.forecast_provider,
            )

        fallback_messages: list[str] = []
        try:
            warnings = self.warning_provider.fetch_warnings(context)
        except Exception as exc:  # noqa: BLE001
            if not self.settings.fallback_to_mock_on_failure:
                self.repository.update_refresh_status("ingestion", error=f"warning provider failed: {exc}")
                raise
            warnings = self.fallback_provider.fetch_warnings(context)
            fallback_messages.append(f"warning provider failed: {exc}")

        try:
            forecast = self.forecast_provider.fetch_forecast(context)
        except Exception as exc:  # noqa: BLE001
            if not self.settings.fallback_to_mock_on_failure:
                self.repository.update_refresh_status("ingestion", error=f"forecast provider failed: {exc}")
                raise
            forecast = self.fallback_provider.fetch_forecast(context)
            fallback_messages.append(f"forecast provider failed: {exc}")

        try:
            self.repository.replace_warnings(warnings)
            self.repository.replace_forecast(forecast)
            status_error = "; ".join(fallback_messages) if fallback_messages else None
            self.repository.update_refresh_status("ingestion", error=status_error)
        except Exception as exc:  # noqa: BLE001
            self.repository.update_refresh_status("ingestion", error=str(exc))
            raise
