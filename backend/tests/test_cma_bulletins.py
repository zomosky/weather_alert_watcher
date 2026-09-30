from datetime import datetime, timedelta, timezone

import pytest

from app.providers.cma_bulletins import parse_bulletin

NOW = datetime(2026, 9, 30, 4, tzinfo=timezone.utc)
URL = "https://www.nmc.cn/publish/weather-bulletin/index.htm"


def page(title="天气公报", author="2026 年 09 月 30 日 08 时", text="预计今天四川、重庆有大暴雨和大风。"):
    return f'<nav>广东台风红色预警</nav><div id="text"><div class="title">{title}</div><div class="author">{author}</div><div class="writing"><p>{text}</p></div></div>'


def test_body_provenance_and_no_invented_warning():
    record = parse_bulletin(page(), URL, NOW)
    assert record.provinces == ["重庆", "四川"]
    assert record.hazard_types == ["暴雨", "大风"]
    assert record.warning_level is None
    assert record.kind == "bulletin"
    assert record.published_at == NOW - timedelta(hours=4)
    assert "广东" not in record.body
    assert record.id == parse_bulletin(page(), URL, NOW + timedelta(minutes=30)).id


def test_official_warning_requires_title_and_publication():
    record = parse_bulletin(page(title="暴雨橙色预警"), URL, NOW)
    assert record.kind == "official_warning"
    assert record.warning_level == "橙色"
    unknown = parse_bulletin(page(title="暴雨橙色预警", author="发布时间未知"), URL, NOW)
    assert unknown.published_at is None
    assert unknown.warning_level is None
    assert unknown.kind == "bulletin"


def test_outlook_does_not_become_today_warning():
    record = parse_bulletin(page(text="未来十天四川有大暴雨"), URL.replace("weather-bulletin/index", "bulletin/mid-range"), NOW)
    assert record.kind == "outlook"
    assert record.warning_level is None


def test_no_single_character_province_alias():
    record = parse_bulletin(page(text="广州有暴雨，推广大风防范措施。"), URL, NOW)
    assert record.provinces == []


def test_southern_qinghai_is_not_hainan():
    record = parse_bulletin(page(text="青海南部有大风。"), URL, NOW)
    assert record.provinces == ["青海"]


@pytest.mark.parametrize("body", ["<nav>广东暴雨</nav>", page(text="当前暂无有效正文。")])
def test_missing_or_non_weather_body_is_failure(body):
    with pytest.raises(ValueError):
        parse_bulletin(body, URL, NOW)


def test_future_publication_is_rejected():
    with pytest.raises(ValueError):
        parse_bulletin(page(author="2026年10月1日08时"), URL, NOW)


def test_midnight_year_boundary_uses_explicit_publication_year():
    record = parse_bulletin(page(author="2025年12月31日23时", text="未来三天四川有暴雪。"), URL, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert record.published_at == datetime(2025, 12, 31, 15, tzinfo=timezone.utc)
