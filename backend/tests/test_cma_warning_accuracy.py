from datetime import datetime, timezone
from pathlib import Path

from app.providers.cma_bulletins import parse_bulletin
from app.providers.cma_provider import warnings_from_bulletins
from app.providers.cma_rules import forecast_periods
import pytest

NOW = datetime(2026, 9, 30, 6, 30, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures" / "nmc"


def official(name, path):
    return parse_bulletin((FIXTURES / (name + ".html")).read_text(), "https://www.nmc.cn/publish/" + path, NOW)


def test_real_generic_title_has_colour_in_official_lead():
    row = official("wind", "country/warning/wind.html")
    assert row.kind == "official_warning" and row.warning_level == "蓝色"
    assert "继续发布大风蓝色预警" in row.title
    assert "海南" not in row.provinces
    warnings = warnings_from_bulletins([row], now=NOW)
    assert {w.province for w in warnings} == set(row.provinces)
    beijing = next(w for w in warnings if w.province == "北京")
    qinghai = next(w for w in warnings if w.province == "青海")
    assert beijing.expires_at == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert qinghai.expires_at == datetime(2026, 10, 2, tzinfo=timezone.utc)


def test_region_specific_time_does_not_extend_other_provinces():
    row = official("wind", "country/warning/wind.html")
    later = datetime(2026, 10, 1, 4, tzinfo=timezone.utc)
    warnings = warnings_from_bulletins([row], now=later)
    assert "北京" not in {w.province for w in warnings}
    assert "青海" in {w.province for w in warnings}


def test_real_joint_warning_does_not_spread_maximum_colour():
    row = official("mountainflood", "mountainflood.html")
    assert row.kind == "official_warning" and row.warning_level == "黄色"
    assert "山洪" in row.hazard_types
    warnings = warnings_from_bulletins([row], now=NOW)
    assert {w.province: w.level for w in warnings} == {"重庆": "蓝色", "贵州": "黄色", "湖北": "蓝色"}
    assert all(w.hazard_type == "山洪" for w in warnings)


def test_real_geohazard_is_recognised_without_rain_keyword():
    row = official("geohazard", "geohazard.html")
    assert row.kind == "official_warning" and "地质灾害" in row.hazard_types
    warnings = warnings_from_bulletins([row], now=NOW)
    assert {w.province for w in warnings} == {"重庆", "湖北", "西藏", "陕西"}
    assert all(w.level == "黄色" for w in warnings)


def test_real_cancellation_never_becomes_active_warning():
    row = official("cancelled", "country/warning/strong_convection.html")
    assert row.kind == "cancelled_warning"
    assert row.warning_level is None
    assert warnings_from_bulletins([row], now=NOW) == []


def test_real_frozen_warning_not_rejected_for_missing_rain_keyword():
    row = official("frozen", "country/warning/frozen.html")
    assert row.kind == "cancelled_warning" and "冰冻" in row.hazard_types
    assert warnings_from_bulletins([row], now=NOW) == []


def test_colours_in_historical_paragraph_do_not_promote_bulletin():
    html = '<div id="text"><div class="title">天气公报</div><div class="author">2026年9月30日08时</div><div class="writing"><p>预计今天四川有降雨。</p><p>回顾：昨日中央气象台发布暴雨橙色预警。</p></div></div>'
    row = parse_bulletin(html, "https://www.nmc.cn/publish/weather-bulletin/index.htm", NOW)
    assert row.warning_level is None and row.kind == "bulletin"


def test_uncoloured_fire_risk_remains_a_risk_notice():
    html = '<div id="text"><div class="title">森林火险预报</div><div class="author">2026年9月30日08时</div><div class="writing"><p>中国气象局发布森林火险气象预报。</p><p>预计新疆北部森林火险气象等级较高。</p></div></div>'
    row = parse_bulletin(html, "https://www.nmc.cn/publish/environment/forestfire-doc.html", NOW)
    assert row.kind == "risk_notice" and row.warning_level is None
    assert warnings_from_bulletins([row], now=NOW) == []


def test_historical_product_and_expired_forecast_never_become_current():
    row = official("geohazard", "geohazard.html")
    assert warnings_from_bulletins([row], now=datetime(2026, 9, 30, 13, tzinfo=timezone.utc)) == []


def test_duplicate_alias_sources_do_not_duplicate_map_warning():
    row = official("wind", "country/warning/wind.html")
    duplicate = official("wind", "country/warning/wind-alias.html")
    assert len(warnings_from_bulletins([row, duplicate], now=NOW)) == len(warnings_from_bulletins([row], now=NOW))


def test_date_only_metadata_combines_only_with_matching_publication_lead():
    row = official("forestfire", "environment/forestfire-doc.html")
    assert row.kind == "risk_notice" and row.warning_level is None
    assert row.published_at == datetime(2026, 9, 29, 10, tzinfo=timezone.utc)
    assert warnings_from_bulletins([row], now=NOW) == []
    mismatched = (FIXTURES / "forestfire.html").read_text().replace('<b>29</b>', '<b>28</b>', 1)
    row = parse_bulletin(mismatched, "https://www.nmc.cn/publish/environment/forestfire-doc.html", NOW)
    assert row.published_at is None  # never use the monitoring period or page-generation time as publication


def test_no_global_colour_but_explicit_regional_risk_is_supported():
    html = '<div id="text"><div class="title">中小河流洪水气象风险预警</div><div class="author">2026年9月30日08时</div><div class="writing"><p>中央气象台9月30日08时发布中小河流洪水气象风险预警：</p><p>预计9月30日08时至10月1日08时，江西南部风险较高（黄色预警），其中，福建东部风险高（橙色预警）。</p></div></div>'
    row = parse_bulletin(html, "https://www.nmc.cn/publish/swdz/zxhlhsqxyj.html", NOW)
    assert row.kind == "official_warning"
    warnings = warnings_from_bulletins([row], now=NOW)
    assert {w.province: w.level for w in warnings} == {"江西": "黄色", "福建": "橙色"}


@pytest.mark.parametrize("stamp,text,end", [
    (datetime(2026, 12, 31, tzinfo=timezone.utc), "12月31日08时至1日08时，四川有大风。", datetime(2027, 1, 1, tzinfo=timezone.utc)),
    (datetime(2024, 2, 29, tzinfo=timezone.utc), "2月29日08时至3月1日08时，四川有大风。", datetime(2024, 3, 1, tzinfo=timezone.utc)),
])
def test_calendar_boundaries_in_explicit_periods(stamp, text, end):
    assert forecast_periods(text, stamp)[0][1] == end


def test_malformed_explicit_period_never_falls_back_to_active_window():
    html = '<div id="text"><div class="title">大风蓝色预警</div><div class="author">2026年9月30日08时</div><div class="writing"><p>预计9月31日08时至10月1日08时，四川有大风。</p></div></div>'
    row = parse_bulletin(html, "https://www.nmc.cn/publish/country/warning/wind.html", NOW)
    assert warnings_from_bulletins([row], now=NOW) == []
