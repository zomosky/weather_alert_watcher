from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db
from app.models import BulletinRecord, ForecastPoint
from app.providers.base import IngestionContext
from app.providers.cma_bulletins import SourceResult, parse_bulletin
from app.providers.cma_provider import warnings_from_bulletins
from app.providers.mock_provider import MockWeatherProvider
from app.services.bulletins import BulletinService, source_key
from app.services.forecast import ForecastService
from app.services.ingestion import IngestionInput, IngestionService
from app.storage.repository import WeatherRepository

URL = "https://www.nmc.cn/publish/weather-bulletin/index.htm"


@pytest.fixture
def repo():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield WeatherRepository(session)
    engine.dispose()


def settings(**kwargs):
    kwargs.setdefault("cma_local_signals_enabled", False)
    return Settings(_env_file=None, warning_provider="cma", forecast_provider="mock", **kwargs)


def bulletin(url=URL, title="天气公报"):
    now = datetime.now(timezone.utc)
    stamp = now.astimezone(timezone(timedelta(hours=8))).strftime("%Y年%m月%d日%H时%M分")
    return parse_bulletin(f'<div id="text"><div class="title">{title}</div><div class="author">{stamp}</div><div class="writing"><p>今天四川有暴雨和大风。</p></div></div>', url, now)


def test_partial_failure_preserves_previous_source_and_is_idempotent(repo):
    second = URL.replace("weather-bulletin/index", "weatherperday/index")
    repo.save_bulletin(bulletin(second))
    service = BulletinService(repo, settings(cma_source_urls=f"{URL},{second}"))
    service.provider.fetch = lambda: [SourceResult(URL, bulletin()), SourceResult(second, error="来源超时")]
    assert service.refresh() == (1, 1)
    service.refresh()
    assert repo.db.scalar(select(func.count()).select_from(BulletinRecord)) == 2
    assert len(repo.list_bulletins()) == 2
    assert repo.get_status(source_key(second)).last_error == "来源超时"
    assert repo.get_status("bulletins").last_success_at is not None


def test_complete_outage_does_not_clear_bulletins(repo):
    repo.save_bulletin(bulletin())
    service = BulletinService(repo, settings(cma_source_urls=URL))
    service.provider.fetch = lambda: [SourceResult(URL, error="全部失败")]
    assert service.refresh() == (0, 1)
    assert len(repo.list_bulletins()) == 1


def test_expired_publication_is_removed_despite_recent_fetch(repo):
    record = bulletin()
    record.published_at = datetime.now(timezone.utc) - timedelta(days=4)
    repo.save_bulletin(record)
    assert repo.list_bulletins(72) == []
    repo.prune_bulletins(72)
    assert repo.db.scalar(select(func.count()).select_from(BulletinRecord)) == 0


def test_forecast_never_substitutes_another_location(repo):
    provider = MockWeatherProvider()
    beijing = IngestionContext(39.9042, 116.4074, "北京", "北京")
    chengdu = IngestionContext(30.5728, 104.0668, "四川", "四川")
    repo.replace_forecast(provider.fetch_forecast(beijing))
    assert repo.list_forecast(chengdu.lat, chengdu.lon) == []
    repo.replace_forecast(provider.fetch_forecast(chengdu))
    assert repo.list_forecast(beijing.lat, beijing.lon)
    assert repo.list_forecast(chengdu.lat, chengdu.lon)


def test_location_forecast_is_fetched_for_requested_coordinates(repo):
    rows = ForecastService(repo, settings()).get(IngestionContext(30.5728, 104.0668, "四川", "四川"))
    assert rows and all(r.lat == 30.5728 and r.lon == 104.0668 for r in rows)


def test_forecast_failure_does_not_block_disclosures(repo):
    service = IngestionService(repo, settings(fallback_to_mock_on_failure=False))
    service.bulletin_service.provider.fetch = lambda: [SourceResult(URL, bulletin())]
    def fail(context):
        raise RuntimeError("预报服务不可用")
    service.forecast_provider.fetch_forecast = fail
    service.refresh(IngestionInput(39.9042, 116.4074, "北京", "北京"))
    assert len(repo.list_bulletins()) == 1
    assert repo.get_status("forecast").last_error
    assert repo.get_status("warnings").last_error is None


def test_warning_colour_only_for_title_hazard_and_cancellation_is_not_active():
    assert warnings_from_bulletins([bulletin()]) == []
    records = warnings_from_bulletins([bulletin(title="暴雨橙色预警")])
    assert records and all(r.hazard_type == "暴雨" and r.level == "橙色" for r in records)
    assert all(r.expires_at is None for r in records)  # source did not disclose expiry
    assert warnings_from_bulletins([bulletin(title="暴雨橙色预警解除")]) == []


def test_map_window_does_not_fabricate_official_expiry(repo):
    records = warnings_from_bulletins([bulletin(title="暴雨橙色预警")])
    repo.replace_warnings(records)
    assert repo.list_warnings(None)
    for row in repo.list_warnings(None):
        row.issue_time = datetime.now(timezone.utc) - timedelta(hours=25)
    repo.db.commit()
    assert repo.list_warnings(None) == []


def test_dashboard_contract_and_utc_provenance(repo, monkeypatch):
    import app.main as main
    import app.api.routes as routes
    config = settings(cma_source_urls=URL)
    monkeypatch.setattr(routes, "get_settings", lambda: config)
    monkeypatch.setattr(main, "engine", repo.db.bind)
    main.app.dependency_overrides[get_db] = lambda: repo.db
    repo.save_bulletin(bulletin())
    try:
        with TestClient(main.app) as client:
            assert client.get("/api/v1/ready").status_code == 200
            response = client.post("/api/v1/dashboard", json={"lat": 30.5728, "lon": 104.0668, "province": "四川"})
        assert response.status_code == 200
        data = response.json()
        assert data["bulletins"][0]["source_url"] == URL
        assert data["bulletins"][0]["published_at"].endswith("Z")
        assert data["forecast_location"] == "四川"
        assert data["forecast_source"] == "MockForecast"
        assert data["source_statuses"]
    finally:
        main.app.dependency_overrides.clear()


def test_bad_provider_setting_fails_instead_of_silently_using_mock():
    with pytest.raises(ValueError):
        Settings(_env_file=None, warning_provider="misspelled-provider")


def test_local_snapshot_replacement_does_not_touch_national_bulletins(repo):
    repo.save_bulletin(bulletin())
    row = bulletin(URL + "local")
    row.kind = "local_signal"
    repo.replace_local_signals([row])
    assert len(repo.list_local_signals()) == 1 and len(repo.list_bulletins()) == 1
    repo.replace_local_signals([])
    assert repo.list_local_signals() == [] and len(repo.list_bulletins()) == 1


def test_partial_local_index_retains_prior_snapshot_and_other_pipelines(repo):
    row = bulletin(URL + "local")
    row.kind = "local_signal"
    repo.replace_local_signals([row])
    service = IngestionService(repo, settings(cma_local_signals_enabled=True))
    service.bulletin_service.provider.fetch = lambda: [SourceResult(URL, bulletin(title="暴雨橙色预警"))]
    def fail():
        raise ValueError("地方预警分页数量变化")
    service.local_signal_service.provider.fetch = fail
    service.refresh(IngestionInput(39.9042, 116.4074, "北京", "北京"))
    assert len(repo.list_local_signals()) == 1
    assert repo.get_status("local_signals").last_error == "地方预警分页数量变化"
    assert repo.list_warnings(None) and repo.get_status("forecast").last_error is None
