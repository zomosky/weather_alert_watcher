"""Official publication statements and region-specific forecast windows only."""
from datetime import datetime, timedelta, timezone
from app.core.config import Settings
from app.models import BulletinRecord, WarningRecord
from app.providers.base import IngestionContext
from app.providers.cma_bulletins import CmaBulletinProvider
from app.providers.cma_rules import RISK_HAZARDS, TIME_RANGE, coloured_regions, extract_provinces, forecast_periods, title_hazard

LEVEL_SCORE = {"蓝色": 1, "黄色": 2, "橙色": 3, "红色": 4}


def warnings_from_bulletins(records: list[BulletinRecord], *, now: datetime | None = None) -> list[WarningRecord]:
    now = now or datetime.now(timezone.utc)
    rows: dict[tuple, WarningRecord] = {}
    for record in records:
        published = record.published_at
        if published and published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if record.kind != "official_warning" or not record.warning_level or not published or published > now + timedelta(minutes=10):
            continue
        hazard = title_hazard(record.title)
        if not hazard:
            continue
        text = record.body.split("防御指南")[0]
        paragraphs = text.splitlines()
        periods = [period for p in paragraphs for period in forecast_periods(p, published)]
        if TIME_RANGE.search(text) and not periods:
            continue  # malformed explicit periods cannot fall back to an assumed current window
        scopes = periods if periods else [(p, None) for p in paragraphs[1:] or paragraphs]
        for region, end in scopes:
            if (end and end <= now) or (not end and published < now - timedelta(hours=24)):
                continue
            areas = coloured_regions(region) if hazard in RISK_HAZARDS else [
                (province, record.warning_level, region) for province in extract_provinces(region)]
            for province, level, excerpt in areas:
                key = (hazard, province, published, record.title)
                previous = rows.get(key)
                if previous and LEVEL_SCORE[previous.level] > LEVEL_SCORE[level]:
                    continue
                if previous and previous.level == level and previous.expires_at and end and previous.expires_at > end:
                    continue
                rows[key] = WarningRecord(source="CMA/NMC", title=record.title, level=level,
                                          hazard_type=hazard, province=province, issue_time=published,
                                          expires_at=end, detail_url=record.source_url,
                                          summary=excerpt[:1024], confidence=1.0)
    return list(rows.values())


class CmaWarningProvider:
    def __init__(self, settings: Settings, ai_extractor=None):
        self.provider = CmaBulletinProvider(settings)

    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        records = [r.record for r in self.provider.fetch() if r.record]
        if not records:
            raise RuntimeError("CMA 公告来源暂不可用")
        return warnings_from_bulletins(records)
