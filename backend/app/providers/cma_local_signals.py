"""Public NMC website index; a listing is not proof of an active warning lifecycle."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.models import BulletinRecord
from app.providers.cma_bulletins import HEADERS
from app.providers.cma_rules import CST, COLOUR, HAZARDS, extract_provinces

LOCAL_INDEX_URL = "https://www.nmc.cn/publish/alarm.html"


class CmaLocalSignalProvider:
    def __init__(self, settings: Settings, *, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client

    def fetch(self, *, now: datetime | None = None) -> list[BulletinRecord]:
        now = now or datetime.now(timezone.utc)
        if self.settings.cma_local_source_url != "https://www.nmc.cn/rest/findAlarm":
            raise ValueError("仅支持已验证的中央气象台公开查询来源")
        if self.client:
            return self._fetch(self.client, now)
        with httpx.Client(timeout=self.settings.http_timeout_seconds, headers=HEADERS) as client:
            return self._fetch(client, now)

    def _fetch(self, client, now):
        def page(number):
            response = client.get(self.settings.cma_local_source_url, params={"pageNo": number, "pageSize": 100})
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0 or not isinstance(data.get("data", {}).get("page"), dict):
                raise ValueError("地方预警索引结构异常")
            result = data["data"]["page"]
            if result.get("pageNo") != number or not isinstance(result.get("list"), list):
                raise ValueError("地方预警分页不匹配")
            return result

        first = page(1)
        total, pages = first.get("count"), first.get("totalPage")
        if not isinstance(total, int) or not isinstance(pages, int) or total < 0 or pages < 0:
            raise ValueError("地方预警分页数量异常")
        if pages > self.settings.cma_local_max_pages:
            raise ValueError("地方预警页数超过配置上限；未截断采集")
        with ThreadPoolExecutor(max_workers=3) as pool:
            rest = list(pool.map(page, range(2, pages + 1)))
        snapshots = [first, *rest]
        if any(p.get("count") != total or p.get("totalPage") != pages for p in snapshots):
            raise ValueError("地方预警索引采集期间数量变化，保留旧快照")
        records = {}
        for snapshot in snapshots:
            for row in snapshot["list"]:
                identifier = row.get("alertid")
                path = row.get("url", "")
                title = row.get("title", "")
                if not isinstance(identifier, str) or not re.fullmatch(r"[0-9_]+", identifier):
                    raise ValueError("地方预警标识异常")
                if path != f"/publish/alarm/{identifier}.html" or not isinstance(title, str) or not title.strip():
                    raise ValueError("地方预警标题或来源链接异常")
                try:
                    published = datetime.strptime(row["issuetime"], "%Y/%m/%d %H:%M").replace(tzinfo=CST).astimezone(timezone.utc)
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError("地方预警发布时间异常") from exc
                if published > now + timedelta(minutes=10):
                    raise ValueError("地方预警发布时间晚于抓取时间")
                colour = re.search(rf"({COLOUR})预警", title)
                level = colour.group(1) if colour and not any(word in title for word in ("解除", "停止", "取消")) else None
                record = BulletinRecord(id=sha256(("nmc-local:" + identifier).encode()).hexdigest(),
                    source="CMA/NMC 地方索引", source_url=urljoin(LOCAL_INDEX_URL, path), title=title[:255],
                    body=title, summary=title, provinces=extract_provinces(title),
                    hazard_types=[name for name, words in HAZARDS if any(word in title for word in words)] or ["其他气象灾害"],
                    kind="local_signal", warning_level=level, published_at=published, fetched_at=now)
                if identifier in records:
                    raise ValueError("地方预警分页重复；可能发生动态翻页，保留旧快照")
                records[identifier] = record
        if len(records) != total:
            raise ValueError("地方预警条数不匹配；保留旧快照")
        return list(records.values())
