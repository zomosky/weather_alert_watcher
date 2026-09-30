from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select, or_, func
from sqlalchemy.orm import Session

from app.models import BulletinRecord, ForecastPoint, RefreshStatus, WarningRecord


class WeatherRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_warnings(self, province: str | None) -> list[WarningRecord]:
        now = datetime.now(timezone.utc)
        stmt = select(WarningRecord).where(
            or_(WarningRecord.expires_at.is_(None), WarningRecord.expires_at > now),
            or_(WarningRecord.source != "CMA/NMC", WarningRecord.expires_at.is_not(None), WarningRecord.issue_time >= now - timedelta(hours=24)),
        ).order_by(WarningRecord.issue_time.desc())
        if province:
            stmt = stmt.where(WarningRecord.province == province)
        return list(self.db.scalars(stmt).all())

    def list_forecast(self, lat: float, lon: float) -> list[ForecastPoint]:
        stmt = (
            select(ForecastPoint)
            .where(ForecastPoint.lat == lat, ForecastPoint.lon == lon, ForecastPoint.forecast_time >= datetime.now(timezone.utc))
            .order_by(ForecastPoint.forecast_time.asc())
        )
        rows = list(self.db.scalars(stmt).all())
        return rows

    def replace_warnings(self, warnings: list[WarningRecord]) -> None:
        self.db.execute(delete(WarningRecord))
        self.db.add_all(warnings)
        self.db.commit()

    def replace_forecast(self, forecast_points: list[ForecastPoint]) -> None:
        if forecast_points:
            self.db.execute(delete(ForecastPoint).where(ForecastPoint.lat == forecast_points[0].lat, ForecastPoint.lon == forecast_points[0].lon))
        self.db.execute(delete(ForecastPoint).where(ForecastPoint.forecast_time < datetime.now(timezone.utc) - timedelta(days=1)))
        self.db.add_all(forecast_points)
        self.db.commit()

    def update_refresh_status(self, pipeline: str, error: str | None = None, *, success: bool | None = None) -> None:
        existing = self.db.scalar(select(RefreshStatus).where(RefreshStatus.pipeline == pipeline))
        now = datetime.now(timezone.utc)
        if existing is None:
            existing = RefreshStatus(pipeline=pipeline)
            self.db.add(existing)
        existing.last_error = error[:1024] if error else None
        successful = success if success is not None else error is None
        if successful:
            existing.last_success_at = now
        existing.updated_at = now
        self.db.commit()

    def get_last_refresh(self, pipeline: str = "ingestion") -> datetime | None:
        existing = self.db.scalar(select(RefreshStatus).where(RefreshStatus.pipeline == pipeline))
        return existing.last_success_at if existing else None

    def save_bulletin(self, record: BulletinRecord) -> None:
        self.db.merge(record)
        self.db.commit()

    def list_bulletins(self, retention_hours: int = 72) -> list[BulletinRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        stmt = select(BulletinRecord).where(BulletinRecord.kind != "local_signal", func.coalesce(BulletinRecord.published_at, BulletinRecord.fetched_at) >= cutoff).order_by(BulletinRecord.fetched_at.desc(), BulletinRecord.published_at.desc())
        latest: dict[str, BulletinRecord] = {}
        for item in self.db.scalars(stmt):
            latest.setdefault(item.source_url, item)
        return list(latest.values())

    def prune_bulletins(self, retention_hours: int) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        self.db.execute(delete(BulletinRecord).where(BulletinRecord.kind != "local_signal", func.coalesce(BulletinRecord.published_at, BulletinRecord.fetched_at) < cutoff))
        self.db.commit()

    def replace_local_signals(self, records: list[BulletinRecord]) -> None:
        self.db.execute(delete(BulletinRecord).where(BulletinRecord.kind == "local_signal"))
        self.db.add_all(records)
        self.db.commit()

    def list_local_signals(self) -> list[BulletinRecord]:
        return list(self.db.scalars(select(BulletinRecord).where(BulletinRecord.kind == "local_signal")
                                   .order_by(BulletinRecord.published_at.desc(), BulletinRecord.id)).all())

    def get_status(self, pipeline: str) -> RefreshStatus | None:
        return self.db.scalar(select(RefreshStatus).where(RefreshStatus.pipeline == pipeline))
