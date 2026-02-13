from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas import DashboardResponse, ForecastPointItem, LocationRequest, ProvinceItem, WarningItem
from app.services.province import sorted_provinces
from app.storage.repository import WeatherRepository

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/dashboard", response_model=DashboardResponse)
def dashboard(payload: LocationRequest, db: Session = Depends(get_db)) -> DashboardResponse:
    settings = get_settings()
    repo = WeatherRepository(db)
    warnings = repo.list_warnings(None)
    forecast_rows = repo.list_forecast(round(payload.lat, 4), round(payload.lon, 4))
    provinces = [
        ProvinceItem(name=item.name, pinyin_initial=item.pinyin_initial, highlighted=item.name == payload.province)
        for item in sorted_provinces(payload.province)
    ]
    return DashboardResponse(
        current_province=payload.province,
        provinces=provinces,
        warnings=[
            WarningItem(
                source=w.source,
                title=w.title,
                level=w.level,
                hazard_type=w.hazard_type,
                province=w.province,
                issue_time=w.issue_time,
                expires_at=w.expires_at,
                detail_url=w.detail_url,
                summary=w.summary,
                confidence=w.confidence,
                is_ai_augmented="LLM" in w.source,
            )
            for w in warnings
        ],
        forecast_points=[
            ForecastPointItem(
                forecast_time=f.forecast_time,
                temperature_c=f.temperature_c,
                humidity_pct=f.humidity_pct,
            )
            for f in forecast_rows
        ],
        last_refresh_at=repo.get_last_refresh("ingestion"),
        refresh_interval_minutes=settings.refresh_interval_minutes,
    )
