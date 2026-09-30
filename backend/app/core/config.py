from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.cma_sources import DEFAULT_WARNING_URLS


class Settings(BaseSettings):
    app_name: str = "weather-alert-watcher-api"
    env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./weather.db"
    refresh_interval_minutes: int = Field(default=30, ge=1, le=1440)
    ai_confidence_threshold: float = 0.65
    http_timeout_seconds: int = Field(default=20, ge=1, le=120)

    warning_provider: Literal["mock", "cma", "nmc", "qweather"] = "cma"
    forecast_provider: Literal["mock", "openmeteo", "qweather"] = "openmeteo"
    fallback_to_mock_on_failure: bool = False
    cma_bulletins_enabled: bool = True
    cma_warning_source_urls: str = DEFAULT_WARNING_URLS
    cma_local_signals_enabled: bool = True
    cma_local_source_url: str = "https://www.nmc.cn/rest/findAlarm"
    cma_local_max_pages: int = Field(default=30, ge=1, le=100)
    bulletin_retention_hours: int = Field(default=72, ge=1, le=720)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    nmc_source_urls: str = (
        "https://www.nmc.cn/publish/weatherperday/index.htm,"
        "https://www.nmc.cn/publish/country/warning/dust.html,"
        "https://www.nmc.cn/publish/weather-bulletin/index.htm"
    )

    # Sources shared with cma_publish. Mid-range is retained as outlook only.
    cma_source_urls: str = (
        "https://www.nmc.cn/publish/weather-bulletin/index.htm,"
        "https://www.nmc.cn/publish/weatherperday/index.htm,"
        "https://www.nmc.cn/publish/typhoon/warning_index.html,"
        "https://www.nmc.cn/publish/bulletin/mid-range.htm,"
        "https://www.nmc.cn/publish/news/weather_new.html"
    )

    qweather_api_base: str = "https://devapi.qweather.com/v7"
    qweather_api_key: str | None = None

    openmeteo_api_base: str = "https://api.open-meteo.com/v1"

    ai_provider: str = "none"
    ai_enabled_for_nmc: bool = True
    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    default_lat: float = 39.9042
    default_lon: float = 116.4074
    default_province: str = "北京"
    default_label: str = "北京"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def nmc_source_urls_list(self) -> list[str]:
        return [item.strip() for item in self.nmc_source_urls.split(",") if item.strip()]

    @property
    def cma_source_urls_list(self) -> list[str]:
        urls = [item.strip().replace("/publish/typhoon/warning_index.html", "/publish/country/warning/typhoon.html")
                for item in (self.cma_source_urls + "," + self.cma_warning_source_urls).split(",") if item.strip()]
        return list(dict.fromkeys(urls))


@lru_cache
def get_settings() -> Settings:
    return Settings()
