from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ForecastPoint, WarningRecord


@dataclass(frozen=True)
class IngestionContext:
    lat: float
    lon: float
    province: str
    label: str


class WarningProvider(Protocol):
    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        ...


class ForecastProvider(Protocol):
    def fetch_forecast(self, context: IngestionContext) -> list[ForecastPoint]:
        ...
