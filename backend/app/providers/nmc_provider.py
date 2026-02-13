from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import Settings
from app.models import WarningRecord
from app.providers.base import IngestionContext
from app.services.ai_extractor import AiExtractor
from app.services.province import PROVINCES

_LEVEL_PATTERNS = ["红色", "橙色", "黄色", "蓝色"]
_HAZARD_KEYWORDS = ["暴雨", "暴雪", "高温", "寒潮", "雷电", "大风", "沙尘", "台风", "强对流", "冰雹"]


class NmcBulletinWarningProvider:
    def __init__(self, settings: Settings, ai_extractor: AiExtractor | None = None):
        self.settings = settings
        self.ai_extractor = ai_extractor

    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        rows: list[WarningRecord] = []
        now = datetime.now(timezone.utc)

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            for source_url in self.settings.nmc_source_urls_list:
                response = client.get(source_url)
                response.raise_for_status()
                body = response.text
                title = _extract_title(body) or "天气公告"
                plain = _to_plain_text(body)
                level = _detect_level(plain)
                hazard = _detect_hazard(plain)
                provinces = _detect_provinces(plain) or [context.province]
                summary = _compact_text(plain)
                confidence = 0.75
                source_name = "NMC"

                if self.settings.ai_enabled_for_nmc and self.ai_extractor is not None:
                    ai_result = self.ai_extractor.extract_bulletin(source_url=source_url, title=title, text=plain)
                    if ai_result is not None and ai_result.confidence >= self.settings.ai_confidence_threshold:
                        summary = ai_result.summary
                        level = ai_result.level
                        hazard = ai_result.hazard_type
                        confidence = ai_result.confidence
                        source_name = "NMC+LLM"

                for province in provinces:
                    rows.append(
                        WarningRecord(
                            source=source_name,
                            title=title,
                            level=level,
                            hazard_type=hazard,
                            province=province,
                            issue_time=now,
                            expires_at=now + timedelta(hours=12),
                            detail_url=source_url,
                            summary=summary,
                            confidence=confidence,
                        )
                    )
        return rows


def _extract_title(html_text: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def _to_plain_text(html_text: str) -> str:
    no_script = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    no_style = re.sub(r"<style[^>]*>.*?</style>", " ", no_script, flags=re.IGNORECASE | re.DOTALL)
    stripped = re.sub(r"<[^>]+>", " ", no_style)
    stripped = html.unescape(stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def _detect_level(text: str) -> str:
    for level in _LEVEL_PATTERNS:
        if level in text:
            return level
    return "蓝色"


def _detect_hazard(text: str) -> str:
    for keyword in _HAZARD_KEYWORDS:
        if keyword in text:
            return keyword
    return "综合风险"


def _detect_provinces(text: str) -> list[str]:
    found: list[str] = []
    for province in PROVINCES:
        if province.name in text:
            found.append(province.name)
    return found


def _compact_text(text: str) -> str:
    if len(text) <= 120:
        return text
    return f"{text[:117]}..."
