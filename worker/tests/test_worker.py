"""Exercise worker entry points without a live source, scheduler loop or database."""
import logging
import socket
import sys
from datetime import timedelta
from types import SimpleNamespace

import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.storage.repository import WeatherRepository
from worker.app import worker


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    config = Settings(
        _env_file=None, warning_provider="mock", forecast_provider="mock",
        cma_bulletins_enabled=False, cma_local_signals_enabled=False,
        ai_provider="none", default_lat=30.5728, default_lon=104.0668,
        default_province="四川", default_label="成都", refresh_interval_minutes=17,
    )
    engine = create_engine("sqlite://", poolclass=StaticPool)
    closed = []

    class TrackedSession(Session):
        def close(self):
            super().close()
            closed.append(self)

    factory = sessionmaker(bind=engine, class_=TrackedSession)
    heartbeat = tmp_path / "weather-worker-health"

    def health_path(path):
        assert path == "/tmp/weather-worker-health"
        return heartbeat

    monkeypatch.setattr(worker, "settings", config)
    monkeypatch.setattr(worker, "engine", engine)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "Path", health_path)
    Base.metadata.create_all(engine)
    yield SimpleNamespace(config=config, engine=engine, sessions=factory,
                          heartbeat=heartbeat, closed=closed)
    engine.dispose()


def assert_refreshed(runtime):
    with runtime.sessions() as db:
        repo = WeatherRepository(db)
        forecast = repo.list_forecast(runtime.config.default_lat, runtime.config.default_lon)
        assert forecast
        assert all(row.lat == 30.5728 and row.lon == 104.0668 for row in forecast)
        assert {row.location_label for row in forecast} == {"成都"}
        assert repo.list_forecast(39.9042, 116.4074) == []
        assert repo.list_warnings(None)
        for pipeline in ("forecast", "warnings", "ingestion"):
            assert repo.get_status(pipeline).last_error is None
            assert repo.get_status(pipeline).last_success_at is not None


def test_run_refresh_persists_configured_location_and_closes_session(runtime):
    worker.run_refresh()

    assert len(runtime.closed) == 1
    assert runtime.heartbeat.is_file()
    assert_refreshed(runtime)


def test_run_refresh_logs_failure_closes_session_and_recovers(runtime, monkeypatch, caplog):
    with monkeypatch.context() as patch:
        def fail_refresh(self, payload):
            raise RuntimeError("collection unavailable")

        patch.setattr(worker.IngestionService, "refresh", fail_refresh)
        with caplog.at_level(logging.ERROR, logger=worker.__name__):
            worker.run_refresh()

    assert "Refresh cycle failed; next scheduled attempt will retry" in caplog.text
    assert len(runtime.closed) == 1
    assert runtime.heartbeat.is_file()
    runtime.heartbeat.unlink()

    worker.run_refresh()

    assert len(runtime.closed) == 2
    assert runtime.heartbeat.is_file()
    assert_refreshed(runtime)


def test_main_once_initializes_storage_refreshes_and_does_not_start_scheduler(runtime, monkeypatch):
    Base.metadata.drop_all(runtime.engine)
    monkeypatch.setattr(sys, "argv", ["weather-worker", "--once"])

    def unexpected_scheduler(*args, **kwargs):
        pytest.fail("--once must exit without creating a scheduler")

    monkeypatch.setattr(worker, "BlockingScheduler", unexpected_scheduler)
    worker.main()

    assert len(runtime.closed) == 1
    assert runtime.heartbeat.is_file()
    assert_refreshed(runtime)


@pytest.mark.parametrize("minutes", [1, 17, 1440])
def test_main_schedules_refresh_with_configured_interval_and_safety_limits(runtime, monkeypatch, minutes):
    runtime.config.refresh_interval_minutes = minutes
    monkeypatch.setattr(sys, "argv", ["weather-worker"])
    started = []

    class InspectableScheduler(BlockingScheduler):
        # 保留真实任务注册与触发器，只替换会阻塞的事件循环。
        def start(self):
            started.append(self)

    monkeypatch.setattr(worker, "BlockingScheduler", InspectableScheduler)
    worker.main()

    assert len(runtime.closed) == 1  # 进入调度循环前先刷新一次。
    assert_refreshed(runtime)
    assert len(started) == 1
    scheduler = started[0]
    assert str(scheduler.timezone) == "Asia/Shanghai"
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "weather_refresh"
    assert job.func is worker.run_refresh
    assert job.trigger.interval == timedelta(minutes=minutes)
    assert str(job.trigger.timezone) == "Asia/Shanghai"
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time == 300
    assert job.args == () and job.kwargs == {}

    job.func(*job.args, **job.kwargs)
    assert runtime.heartbeat.is_file()
    assert_refreshed(runtime)


def test_worker_suite_shares_the_offline_guard():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        with pytest.raises(pytest.fail.Exception, match="Network access is disabled"):
            client.sendto(b"test", ("127.0.0.1", 9))
