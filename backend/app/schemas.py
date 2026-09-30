from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class UtcModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def utc_datetime(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class LocationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    address: str | None = None
    province: str | None = None


class ProvinceItem(BaseModel):
    name: str
    pinyin_initial: str
    highlighted: bool = False


class WarningItem(UtcModel):
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


class ForecastPointItem(UtcModel):
    forecast_time: datetime
    temperature_c: float
    humidity_pct: float


class BulletinItem(UtcModel):
    id: str
    source: str
    source_url: str
    title: str
    summary: str
    provinces: list[str]
    hazard_types: list[str]
    kind: str
    warning_level: str | None
    published_at: datetime | None
    fetched_at: datetime


class SourceStatusItem(UtcModel):
    name: str
    provider: str
    state: str
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    message: str | None
    source_url: str | None = None


class DashboardResponse(UtcModel):
    current_province: str | None
    provinces: list[ProvinceItem]
    warnings: list[WarningItem]
    forecast_points: list[ForecastPointItem]
    last_refresh_at: datetime | None
    refresh_interval_minutes: int
    bulletins: list[BulletinItem] = Field(default_factory=list)
    local_signals: list[BulletinItem] = Field(default_factory=list)
    source_statuses: list[SourceStatusItem] = Field(default_factory=list)
    forecast_source: str | None = None
    forecast_location: str | None = None
