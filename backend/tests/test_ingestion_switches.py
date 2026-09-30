"""CMA warning collection stays independent of the bulletin display switch."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.providers.cma_bulletins import CmaBulletinProvider, SourceResult, parse_bulletin
from app.providers.cma_provider import warnings_from_bulletins
from app.services.ingestion import IngestionInput, IngestionService
from app.storage.repository import WeatherRepository

URL = "https://www.nmc.cn/publish/weather-bulletin/index.htm"
PAYLOAD = IngestionInput(30.5728, 104.0668, "四川", "四川")


@pytest.fixture
def repo():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield WeatherRepository(session)
    engine.dispose()


def warning_bulletin():
    now = datetime.now(timezone.utc)
    stamp = now.astimezone(timezone(timedelta(hours=8))).strftime("%Y年%m月%d日%H时%M分")
    html = f'<div id="text"><div class="title">暴雨橙色预警</div><div class="author">{stamp}</div><div class="writing"><p>今天四川有暴雨。</p></div></div>'
    return parse_bulletin(html, URL, now)


def config(enabled):
    return Settings(_env_file=None, warning_provider="cma", forecast_provider="mock",
                    cma_bulletins_enabled=enabled, cma_source_urls=URL,
                    fallback_to_mock_on_failure=False)


def test_disabled_bulletins_still_refresh_official_cma_warnings(repo, monkeypatch):
    record = warning_bulletin()
    monkeypatch.setattr(CmaBulletinProvider, "fetch", lambda self: [SourceResult(URL, record=record)])
    IngestionService(repo, config(False)).refresh(PAYLOAD)

    warnings = repo.list_warnings(None)
    assert [(w.source, w.province, w.level) for w in warnings] == [("CMA/NMC", "四川", "橙色")]
    assert repo.get_status("warnings").last_success_at is not None
    assert repo.get_status("warnings").last_error is None
    assert repo.get_status("ingestion").last_error is None
    assert repo.list_bulletins() == []
    assert repo.get_status("bulletins") is None
    assert repo.list_forecast(PAYLOAD.lat, PAYLOAD.lon)


def test_disabled_bulletins_outage_preserves_official_warnings_without_mock(repo, monkeypatch):
    repo.replace_warnings(warnings_from_bulletins([warning_bulletin()]))
    monkeypatch.setattr(CmaBulletinProvider, "fetch", lambda self: [SourceResult(URL, error="来源超时")])
    service = IngestionService(repo, config(False))
    service.settings.fallback_to_mock_on_failure = True
    service.refresh(PAYLOAD)

    warnings = repo.list_warnings(None)
    assert [(w.source, w.province, w.level) for w in warnings] == [("CMA/NMC", "四川", "橙色")]
    assert repo.get_status("warnings").last_error
    assert repo.get_status("warnings").last_success_at is None
    assert repo.get_status("forecast").last_error is None
    assert repo.list_bulletins() == []


def test_enabled_bulletins_reuse_collection_for_official_warnings(repo, monkeypatch):
    record = warning_bulletin()
    monkeypatch.setattr(CmaBulletinProvider, "fetch", lambda self: [SourceResult(URL, record=record)])
    service = IngestionService(repo, config(True))

    def unexpected_fetch(context):
        raise AssertionError("Enabled bulletin pipeline must supply warnings without a second fetch")

    service.warning_provider.fetch_warnings = unexpected_fetch
    service.refresh(PAYLOAD)

    assert len(repo.list_bulletins()) == 1
    assert [(w.source, w.province) for w in repo.list_warnings(None)] == [("CMA/NMC", "四川")]
    assert repo.get_status("warnings").last_error is None


def test_disabled_bulletins_successful_empty_warning_result_clears_old_warnings(repo, monkeypatch):
    repo.replace_warnings(warnings_from_bulletins([warning_bulletin()]))
    record = warning_bulletin()
    record.warning_level = None
    monkeypatch.setattr(CmaBulletinProvider, "fetch", lambda self: [SourceResult(URL, record=record)])
    IngestionService(repo, config(False)).refresh(PAYLOAD)

    assert repo.list_warnings(None) == []
    assert repo.get_status("warnings").last_error is None
    assert repo.get_status("warnings").last_success_at is not None
