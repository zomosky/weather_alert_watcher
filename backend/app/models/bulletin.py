from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BulletinRecord(Base):
    __tablename__ = "bulletin_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), default="CMA/NMC", nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provinces: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    hazard_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    warning_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
