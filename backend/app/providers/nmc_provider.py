"""NMC compatibility adapter using the same explicit official-warning rules."""
from app.providers.cma_provider import CmaWarningProvider


class NmcBulletinWarningProvider(CmaWarningProvider):
    def __init__(self, settings, ai_extractor=None):
        super().__init__(settings.model_copy(update={"cma_source_urls": settings.nmc_source_urls}), ai_extractor)
