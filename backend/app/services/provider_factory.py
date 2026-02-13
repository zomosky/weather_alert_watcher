from __future__ import annotations

from app.core.config import Settings
from app.providers.base import ForecastProvider, WarningProvider
from app.providers.mock_provider import MockWeatherProvider
from app.providers.nmc_provider import NmcBulletinWarningProvider
from app.providers.openmeteo_provider import OpenMeteoForecastProvider
from app.providers.qweather_provider import QWeatherProvider
from app.services.ai_extractor import AiExtractor


def build_warning_provider(settings: Settings, ai_extractor: AiExtractor) -> WarningProvider:
    provider = settings.warning_provider.lower()
    if provider == "nmc":
        return NmcBulletinWarningProvider(settings=settings, ai_extractor=ai_extractor)
    if provider == "qweather":
        return QWeatherProvider(settings=settings)
    return MockWeatherProvider()


def build_forecast_provider(settings: Settings) -> ForecastProvider:
    provider = settings.forecast_provider.lower()
    if provider == "openmeteo":
        return OpenMeteoForecastProvider(settings=settings)
    if provider == "qweather":
        return QWeatherProvider(settings=settings)
    return MockWeatherProvider()
