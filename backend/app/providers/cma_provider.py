"""Official title colours and timestamps only; no intensity-to-colour inference."""
from datetime import datetime, timedelta, timezone
from app.core.config import Settings
from app.models import BulletinRecord, WarningRecord
from app.providers.base import IngestionContext
from app.providers.cma_bulletins import CmaBulletinProvider


def warnings_from_bulletins(records: list[BulletinRecord]) -> list[WarningRecord]:
    now = datetime.now(timezone.utc)
    rows = []
    for record in records:
        published = record.published_at
        if published and published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if not record.warning_level or not published or published < now - timedelta(hours=24):
            continue
        hazard = next((h for h in record.hazard_types if h in record.title), None)
        if not hazard:
            continue
        for province in record.provinces:
            rows.append(WarningRecord(source="CMA/NMC", title=record.title, level=record.warning_level,
                                      hazard_type=hazard, province=province, issue_time=published,
                                      expires_at=None, detail_url=record.source_url,
                                      summary=record.summary[:1024], confidence=1.0))
    return rows


class CmaWarningProvider:
    def __init__(self, settings: Settings, ai_extractor=None):
        self.provider = CmaBulletinProvider(settings)

    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        records = [r.record for r in self.provider.fetch() if r.record]
        if not records:
            raise RuntimeError("CMA 公告来源暂不可用")
        return warnings_from_bulletins(records)
