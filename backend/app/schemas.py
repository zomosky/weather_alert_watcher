from datetime import datetime
from pydantic import BaseModel, Field


class LocationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    address: str | None = None
    province: str | None = None


class ProvinceItem(BaseModel):
    name: str
    pinyin_initial: str
    highlighted: bool = False


class WarningItem(BaseModel):
    source: str
    title: str
    level: str
    hazard_type: str
    province: str
    issue_time: datetime
    expires_at: datetime | None
    detail_url: str
    summary: str
    confidence: float
    is_ai_augmented: bool = False


class ForecastPointItem(BaseModel):
    forecast_time: datetime
    temperature_c: float
    humidity_pct: float


class DashboardResponse(BaseModel):
    current_province: str | None
    provinces: list[ProvinceItem]
    warnings: list[WarningItem]
    forecast_points: list[ForecastPointItem]
    last_refresh_at: datetime | None
    refresh_interval_minutes: int
