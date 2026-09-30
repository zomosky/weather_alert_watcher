from hashlib import sha256

from app.core.config import Settings
from app.providers.cma_bulletins import CmaBulletinProvider
from app.storage.repository import WeatherRepository


def source_key(url: str) -> str:
    return "cma:" + sha256(url.encode()).hexdigest()[:24]


class BulletinService:
    def __init__(self, repository: WeatherRepository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self.provider = CmaBulletinProvider(settings)

    def refresh(self) -> tuple[int, int]:
        results = self.provider.fetch()
        succeeded = 0
        for result in results:
            if result.record:
                self.repository.save_bulletin(result.record)
                succeeded += 1
            self.repository.update_refresh_status(source_key(result.url), error=result.error)
        self.repository.prune_bulletins(self.settings.bulletin_retention_hours)
        failed = len(results) - succeeded
        self.repository.update_refresh_status("bulletins", error=f"{failed}/{len(results)} 个公告来源异常" if failed else None, success=succeeded > 0)
        return succeeded, failed
