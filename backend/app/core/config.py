from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "weather-alert-watcher-api"
    env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./weather.db"
    refresh_interval_minutes: int = 30
    ai_confidence_threshold: float = 0.65
    http_timeout_seconds: int = 20

    warning_provider: str = "mock"
    forecast_provider: str = "mock"
    fallback_to_mock_on_failure: bool = True

    nmc_source_urls: str = (
        "https://www.nmc.cn/publish/weatherperday/index.htm,"
        "https://www.nmc.cn/publish/country/warning/dust.html,"
        "https://www.nmc.cn/publish/weather-bulletin/index.htm"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def nmc_source_urls_list(self) -> list[str]:
        return [item.strip() for item in self.nmc_source_urls.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
