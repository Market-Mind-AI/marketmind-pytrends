import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrendRequest(Base):
    __tablename__ = "trend_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)
    language: Mapped[str | None] = mapped_column(nullable=True)
    timeframe: Mapped[str | None] = mapped_column(nullable=True)
    endpoint: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="trend_requests")  # type: ignore[name-defined]  # noqa: F821
    raw_api_responses: Mapped[list["RawApiResponse"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    keyword_search_volume_records: Mapped[list["KeywordSearchVolume"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    keyword_related_records: Mapped[list["KeywordRelated"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_trend_requests_keyword", "keyword"),
        Index("ix_trend_requests_country", "country"),
        Index("ix_trend_requests_endpoint", "endpoint"),
        Index("ix_trend_requests_ingestion_run_id", "ingestion_run_id"),
    )
