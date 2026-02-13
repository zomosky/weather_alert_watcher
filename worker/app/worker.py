from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.services.ingestion import IngestionInput, IngestionService
from app.storage.repository import WeatherRepository

settings = get_settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)


def run_refresh() -> None:
    db = SessionLocal()
    try:
        repository = WeatherRepository(db)
        service = IngestionService(repository, settings=settings)
        service.refresh(
            IngestionInput(
                lat=settings.default_lat,
                lon=settings.default_lon,
                province=settings.default_province,
                label=settings.default_label,
            )
        )
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    scheduler = BlockingScheduler()
    scheduler.add_job(run_refresh, "interval", minutes=settings.refresh_interval_minutes, id="weather_refresh", replace_existing=True)
    run_refresh()
    scheduler.start()


if __name__ == "__main__":
    main()
