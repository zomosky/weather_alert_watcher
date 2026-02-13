from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ForecastPoint, RefreshStatus, WarningRecord


class WeatherRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_warnings(self, province: str | None) -> list[WarningRecord]:
        stmt = select(WarningRecord).order_by(WarningRecord.issue_time.desc())
        if province:
            stmt = stmt.where(WarningRecord.province == province)
        return list(self.db.scalars(stmt).all())

    def list_forecast(self, lat: float, lon: float) -> list[ForecastPoint]:
        stmt = (
            select(ForecastPoint)
            .where(ForecastPoint.lat == lat, ForecastPoint.lon == lon)
            .order_by(ForecastPoint.forecast_time.asc())
        )
        rows = list(self.db.scalars(stmt).all())
        if rows:
            return rows
        # fallback to same province not available in V1; return most recent location
        fallback_stmt = select(ForecastPoint).order_by(ForecastPoint.created_at.desc(), ForecastPoint.forecast_time.asc())
        return list(self.db.scalars(fallback_stmt).all())

    def replace_warnings(self, warnings: list[WarningRecord]) -> None:
        self.db.execute(delete(WarningRecord))
        self.db.add_all(warnings)
        self.db.commit()

    def replace_forecast(self, forecast_points: list[ForecastPoint]) -> None:
        self.db.execute(delete(ForecastPoint))
        self.db.add_all(forecast_points)
        self.db.commit()

    def update_refresh_status(self, pipeline: str, error: str | None = None) -> None:
        existing = self.db.scalar(select(RefreshStatus).where(RefreshStatus.pipeline == pipeline))
        now = datetime.now(timezone.utc)
        if existing is None:
            existing = RefreshStatus(pipeline=pipeline)
            self.db.add(existing)
        existing.last_error = error
        if error is None:
            existing.last_success_at = now
        existing.updated_at = now
        self.db.commit()

    def get_last_refresh(self, pipeline: str = "ingestion") -> datetime | None:
        existing = self.db.scalar(select(RefreshStatus).where(RefreshStatus.pipeline == pipeline))
        return existing.last_success_at if existing else None
