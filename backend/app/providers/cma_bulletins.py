"""Portable adaptation of cma_publish's source collection and provenance.

No sibling directory, private settings, LLM, SMTP, or inferred warning colours.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx

from app.core.config import Settings
from app.models import BulletinRecord
from app.providers.cma_rules import CST, HAZARDS, extract_provinces, warning_statement

HEADERS = {"User-Agent": "Mozilla/5.0 WeatherAlertWatcher/0.2", "Accept-Language": "zh-CN,zh;q=0.9"}


def publication_time(text: str) -> datetime | None:
    compact = re.sub(r"\s+", "", text)
    match = re.search(r"(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?(?:T)?(\d{1,2})[时:](\d{1,2})?", compact)
    if not match:
        return None
    year, month, day, hour, minute = match.groups()
    try:
        return datetime(int(year), int(month), int(day), int(hour), int(minute or 0), tzinfo=CST).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_bulletin(html: str, url: str, fetched_at: datetime) -> BulletinRecord:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#text .writing, .writing, article .article-content, .article-content")
    if content is None:
        raise ValueError("未找到公告正文容器")
    for node in content.select("script, style, nav, footer"):
        node.decompose()
    paragraphs = [p.get_text("", strip=True) for p in content.select("p")]
    body = "\n".join(p for p in paragraphs if p) if paragraphs else content.get_text("\n", strip=True)
    body = body.strip()[:32000]
    hazards = [name for name, words in HAZARDS if any(word in body for word in words)]
    if not hazards:
        raise ValueError("正文没有可识别的天气信息")
    title_node = soup.select_one("#text .title, .article-title, h1")
    title = re.sub(r"\s+", "", title_node.get_text() if title_node else "中央气象台天气公告")[:255]
    author = soup.select_one("#text .author, .author, .publish-time, time")
    author_text = re.sub(r"\s+", "", author.get_text("", strip=True)) if author else ""
    published = publication_time(author_text)
    if published is None:
        # Some products disclose the calendar date in metadata and the hour in their publication lead.
        date = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", author_text)
        lead = re.sub(r"\s+", "", body.splitlines()[0])
        clock = re.search(r"(\d{1,2})月(\d{1,2})日(\d{1,2})时(?:(\d{1,2})分)?(?:继续|联合)?发布", lead)
        if date and clock and (int(date[2]), int(date[3])) == (int(clock[1]), int(clock[2])):
            published = publication_time(f"{date[1]}年{clock[1]}月{clock[2]}日{clock[3]}时{clock[4] or '0'}分")
    if published and published > fetched_at + timedelta(minutes=10):
        raise ValueError("公告发布时间晚于抓取时间")
    provinces = extract_provinces(body)
    kind = "outlook" if "mid-range" in url or "中期" in title else "bulletin"
    if kind == "bulletin" and any(word in title for word in ("风险", "火险", "山洪", "地质灾害")):
        kind = "risk_notice"
    level = None
    if kind != "outlook" and published:
        detected, level, statement = warning_statement(title, body)
        if detected != "bulletin":
            kind = detected
            title = statement[:255]
    relevant = [p for p in body.splitlines() if any(word in p for _, words in HAZARDS for word in words)]
    summary = (body if kind in {"official_warning", "cancelled_warning", "risk_notice"} else "\n".join(relevant))[:1200]
    identity = sha256(f"{url}\n{published.isoformat() if published else ''}\n{title}\n{body}".encode()).hexdigest()
    return BulletinRecord(id=identity, source="CMA/NMC", source_url=url, title=title, body=body,
                          summary=summary, provinces=provinces, hazard_types=hazards, kind=kind,
                          warning_level=level, published_at=published, fetched_at=fetched_at)


@dataclass
class SourceResult:
    url: str
    record: BulletinRecord | None = None
    error: str | None = None


class CmaBulletinProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch_one(self, url: str) -> SourceResult:
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"} or parsed.hostname not in {"www.nmc.cn", "nmc.cn"}:
            return SourceResult(url, error="仅支持中央气象台公开来源域名")
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.settings.http_timeout_seconds, headers=HEADERS, follow_redirects=True) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    if response.url.host not in {"www.nmc.cn", "nmc.cn"}:
                        raise ValueError("来源重定向到非中央气象台域名")
                    record = parse_bulletin(response.text, url, datetime.now(timezone.utc))
                    return SourceResult(url, record=record)
            except Exception as exc:
                if attempt == 1:
                    # Do not expose credentials or proxy settings in public status.
                    return SourceResult(url, error=f"采集或解析失败（{type(exc).__name__}）")
        raise AssertionError("unreachable")

    def fetch(self) -> list[SourceResult]:
        urls = list(dict.fromkeys(self.settings.cma_source_urls_list))
        if not urls:
            raise ValueError("CMA_SOURCE_URLS 不能为空")
        with ThreadPoolExecutor(max_workers=min(5, len(urls))) as pool:
            return list(pool.map(self.fetch_one, urls))
