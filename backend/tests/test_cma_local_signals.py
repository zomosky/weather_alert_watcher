from datetime import datetime, timezone

import httpx
import pytest

from app.core.config import Settings
from app.providers.cma_local_signals import CmaLocalSignalProvider

NOW = datetime(2026, 9, 30, 6, 30, tzinfo=timezone.utc)


def item(number, title="四川省阿坝州壤塘县气象台发布雷电黄色预警信号"):
    return {"alertid": str(number), "title": title, "issuetime": "2026/09/30 14:07",
            "url": f"/publish/alarm/{number}.html"}


def provider(handler, max_pages=30):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    config = Settings(_env_file=None, cma_local_max_pages=max_pages)
    return CmaLocalSignalProvider(config, client=client)


def response(request, rows, count=2, page=1, pages=2):
    return httpx.Response(200, json={"code": 0, "data": {"page": {
        "pageNo": page, "pageSize": 1, "count": count, "totalPage": pages, "list": rows}}})


def test_every_page_is_collected_and_local_scope_is_preserved():
    visited = []
    def handler(req):
        number = int(req.url.params["pageNo"])
        visited.append(number)
        return response(req, [item(number)], page=number)
    records = provider(handler).fetch(now=NOW)
    assert sorted(visited) == [1, 2] and len(records) == 2
    assert records[0].provinces == ["四川"]
    assert records[0].kind == "local_signal" and records[0].warning_level == "黄色"
    assert records[0].body == records[0].title  # no invented original warning body/expiry


@pytest.mark.parametrize("failure", ["duplicate", "count_change", "wrong_page", "foreign_url", "future"])
def test_incomplete_or_untrusted_snapshot_is_rejected(failure):
    def handler(req):
        page = int(req.url.params["pageNo"])
        record = item(1 if failure == "duplicate" else page)
        if failure == "foreign_url": record["url"] = "https://example.com/private"
        if failure == "future": record["issuetime"] = "2026/10/30 14:00"
        return response(req, [record], count=3 if failure == "count_change" and page == 2 else 2,
                        page=1 if failure == "wrong_page" else page)
    with pytest.raises(ValueError): provider(handler).fetch(now=NOW)


def test_page_cap_is_an_error_instead_of_silent_truncation():
    with pytest.raises(ValueError, match="上限"):
        provider(lambda req: response(req, [item(1)]), max_pages=1).fetch(now=NOW)


def test_waf_html_200_is_not_a_success():
    with pytest.raises(ValueError):
        provider(lambda req: httpx.Response(200, text="WEB 应用防火墙")).fetch(now=NOW)


def test_empty_list_is_valid_only_when_counts_agree():
    assert provider(lambda req: response(req, [], count=0, pages=0)).fetch(now=NOW) == []


def test_unknown_hazard_is_retained_and_cancellation_has_no_colour():
    title = "辽宁省气象台解除其它气象灾害蓝色预警"
    rows = provider(lambda req: response(req, [item(1, title)], count=1, pages=1)).fetch(now=NOW)
    assert rows[0].hazard_types == ["其他气象灾害"] and rows[0].warning_level is None
