from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.providers.base import IngestionContext
from app.providers.cma_local_signals import LOCAL_INDEX_URL
from app.schemas import BulletinItem, DashboardResponse, ForecastPointItem, LocationRequest, ProvinceItem, SourceStatusItem, WarningItem
from app.services.bulletins import source_key
from app.services.forecast import ForecastService, forecast_key
from app.services.province import sorted_provinces
from app.storage.repository import WeatherRepository

router = APIRouter()


def bulletin_item(b):
    return BulletinItem(id=b.id, source=b.source, source_url=b.source_url, title=b.title, summary=b.summary,
                        provinces=b.provinces, hazard_types=b.hazard_types, kind=b.kind, warning_level=b.warning_level,
                        published_at=b.published_at, fetched_at=b.fetched_at)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}


def source_status(repo, settings, pipeline, name, provider, enabled=True, url=None):
    status = repo.get_status(pipeline)
    last_success = status.last_success_at if status else None
    if last_success and last_success.tzinfo is None:
        last_success = last_success.replace(tzinfo=timezone.utc)
    if not enabled:
        state = "disabled"
    elif provider == "mock":
        state = "demo"
    elif status and status.last_error:
        state = "degraded"
    elif last_success is None:
        state = "waiting"
    elif last_success < datetime.now(timezone.utc) - timedelta(minutes=settings.refresh_interval_minutes * 2):
        state = "stale"
    else:
        state = "ok"
    return SourceStatusItem(name=name, provider=provider, state=state, last_success_at=last_success,
                            last_attempt_at=status.updated_at if status else None,
                            message=status.last_error if status else None, source_url=url)


@router.post("/dashboard", response_model=DashboardResponse)
def dashboard(payload: LocationRequest, db: Session = Depends(get_db)) -> DashboardResponse:
    settings = get_settings()
    repo = WeatherRepository(db)
    warnings = repo.list_warnings(None)
    context = IngestionContext(lat=payload.lat, lon=payload.lon, province=payload.province or "未指定", label=payload.address or payload.province or "自选位置")
    forecast_rows = ForecastService(repo, settings).get(context)
    key = forecast_key(round(payload.lat, 4), round(payload.lon, 4))
    forecast_pipeline = key if repo.get_status(key) else "forecast"
    statuses = [
        source_status(repo, settings, "warnings", "正式预警", settings.warning_provider),
        source_status(repo, settings, forecast_pipeline, "当前坐标预报", settings.forecast_provider),
        source_status(repo, settings, "bulletins", "CMA 公开消息", "CMA/NMC", settings.cma_bulletins_enabled),
        source_status(repo, settings, "local_signals", "地方预警分页索引", "CMA/NMC 地方索引", settings.cma_local_signals_enabled, LOCAL_INDEX_URL),
    ]
    for url in settings.cma_source_urls_list:
        statuses.append(source_status(repo, settings, source_key(url), url.split("/publish/")[-1], "CMA/NMC", settings.cma_bulletins_enabled, url))
    provinces = [ProvinceItem(name=item.name, pinyin_initial=item.pinyin_initial, highlighted=item.name == payload.province) for item in sorted_provinces(payload.province)]
    return DashboardResponse(
        current_province=payload.province, provinces=provinces,
        warnings=[WarningItem(source=w.source, title=w.title, level=w.level, hazard_type=w.hazard_type,
                              province=w.province, issue_time=w.issue_time, expires_at=w.expires_at,
                              detail_url=w.detail_url, summary=w.summary, confidence=w.confidence,
                              is_ai_augmented="LLM" in w.source) for w in warnings],
        forecast_points=[ForecastPointItem(forecast_time=f.forecast_time, temperature_c=f.temperature_c, humidity_pct=f.humidity_pct) for f in forecast_rows],
        last_refresh_at=repo.get_last_refresh("ingestion"), refresh_interval_minutes=settings.refresh_interval_minutes,
        bulletins=[bulletin_item(b)
                   for b in repo.list_bulletins(settings.bulletin_retention_hours)] if settings.cma_bulletins_enabled else [],
        local_signals=[bulletin_item(b) for b in repo.list_local_signals()] if settings.cma_local_signals_enabled else [],
        source_statuses=statuses, forecast_source=forecast_rows[0].source if forecast_rows else None,
        forecast_location=forecast_rows[0].location_label if forecast_rows else None,
    )
