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
    interest_over_time_records: Mapped[list["InterestOverTime"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    interest_by_region_records: Mapped[list["InterestByRegion"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    interest_by_country_records: Mapped[list["InterestByCountry"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    interest_by_region_worldwide_records: Mapped[list["InterestByRegionWorldwide"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="trend_request"
    )
    related_queries: Mapped[list["RelatedQuery"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    related_topics: Mapped[list["RelatedTopic"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821
    trending_rss_records: Mapped[list["TrendingRss"]] = relationship(back_populates="trend_request")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_trend_requests_keyword", "keyword"),
        Index("ix_trend_requests_country", "country"),
        Index("ix_trend_requests_endpoint", "endpoint"),
        Index("ix_trend_requests_ingestion_run_id", "ingestion_run_id"),
    )
