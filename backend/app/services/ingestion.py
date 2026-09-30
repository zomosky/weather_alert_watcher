from dataclasses import dataclass
import logging
from app.core.config import Settings, get_settings
from app.providers.base import IngestionContext
from app.providers.cma_provider import warnings_from_bulletins
from app.providers.mock_provider import MockWeatherProvider
from app.services.ai_extractor import AiExtractor
from app.services.bulletins import BulletinService
from app.services.local_signals import LocalSignalService
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
        self.warning_provider = build_warning_provider(self.settings, AiExtractor(self.settings))
        self.forecast_provider = build_forecast_provider(self.settings)
        self.bulletin_service = BulletinService(repository, self.settings)
        self.local_signal_service = LocalSignalService(repository, self.settings)
        self.fallback_provider = MockWeatherProvider()

    def refresh(self, payload: IngestionInput) -> None:
        context = IngestionContext(**vars(payload))
        errors = []
        cma_success = 0
        cma_failed = 0
        if self.settings.cma_local_signals_enabled:
            try:
                self.local_signal_service.refresh()
            except Exception as exc:
                self.repository.db.rollback()
                logger.exception("Local signal index refresh failed")
                message = str(exc) if isinstance(exc, ValueError) else f"地方索引采集失败（{type(exc).__name__}）"
                self.repository.update_refresh_status("local_signals", error=message)
                errors.append("地方预警索引采集不完整")
        if self.settings.cma_bulletins_enabled:
            try:
                cma_success, cma_failed = self.bulletin_service.refresh()
                if cma_failed:
                    errors.append("部分 CMA 来源暂不可用")
            except Exception:
                self.repository.db.rollback()
                logger.exception("Bulletin refresh failed")
                self.repository.update_refresh_status("bulletins", error="公告刷新失败")
                errors.append("CMA 公告刷新失败")
        for pipeline, provider, fetch, store in [
            ("warnings", self.warning_provider, "fetch_warnings", self.repository.replace_warnings),
            ("forecast", self.forecast_provider, "fetch_forecast", self.repository.replace_forecast),
        ]:
            try:
                if (
                    pipeline == "warnings"
                    and self.settings.warning_provider == "cma"
                    and self.settings.cma_bulletins_enabled
                ):
                    if not cma_success:
                        raise RuntimeError("CMA 来源暂不可用，保留尚未过期的已有预警")
                    data = warnings_from_bulletins(self.repository.list_bulletins(self.settings.bulletin_retention_hours))
                else:
                    data = getattr(provider, fetch)(context)
                if pipeline == "forecast" and not data:
                    raise ValueError("预报来源返回空数据")
                store(data)
                partial = "部分 CMA 来源异常" if pipeline == "warnings" and self.settings.warning_provider == "cma" and cma_failed else None
                self.repository.update_refresh_status(pipeline, error=partial, success=True)
            except Exception:
                self.repository.db.rollback()
                logger.exception("%s refresh failed", pipeline)
                allow_mock = self.settings.fallback_to_mock_on_failure and not (pipeline == "warnings" and self.settings.warning_provider == "cma")
                if allow_mock:
                    try:
                        store(getattr(self.fallback_provider, fetch)(context))
                    except Exception:
                        self.repository.db.rollback()
                        logger.exception("%s mock fallback failed", pipeline)
                self.repository.update_refresh_status(pipeline, error="来源不可用；已启用演示回退" if allow_mock else "来源不可用；保留已有数据")
                errors.append(f"{pipeline} 来源不可用")
        self.repository.update_refresh_status("ingestion", error="；".join(errors) if errors else None)
