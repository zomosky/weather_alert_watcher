from app.core.config import Settings
from app.providers.cma_local_signals import CmaLocalSignalProvider
from app.storage.repository import WeatherRepository


class LocalSignalService:
    def __init__(self, repository: WeatherRepository, settings: Settings):
        self.repository = repository
        self.provider = CmaLocalSignalProvider(settings)

    def refresh(self):
        records = self.provider.fetch()
        self.repository.replace_local_signals(records)
        self.repository.update_refresh_status("local_signals")
        return len(records)
