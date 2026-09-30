import argparse
import logging
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from app.core.config import get_settings
from app.core.database import Base, engine, SessionLocal
from app.services.ingestion import IngestionInput, IngestionService
from app.storage.repository import WeatherRepository

settings = get_settings()
logger = logging.getLogger(__name__)


def run_refresh() -> None:
    try:
        with SessionLocal() as db:
            IngestionService(WeatherRepository(db), settings).refresh(
                IngestionInput(settings.default_lat, settings.default_lon, settings.default_province, settings.default_label))
    except Exception:
        logger.exception("Refresh cycle failed; next scheduled attempt will retry")
    finally:
        Path("/tmp/weather-worker-health").touch()


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather ingestion worker")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    Base.metadata.create_all(bind=engine)
    run_refresh()
    if args.once:
        return
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(run_refresh, "interval", minutes=settings.refresh_interval_minutes,
                      id="weather_refresh", replace_existing=True, max_instances=1, coalesce=True,
                      misfire_grace_time=300)
    scheduler.start()


if __name__ == "__main__":
    main()
