import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterestByRegionWorldwide(Base):
    __tablename__ = "interest_by_region_worldwide"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)
    region_code: Mapped[str] = mapped_column(nullable=False)
    region_name: Mapped[str | None] = mapped_column(nullable=True)
    term: Mapped[str] = mapped_column(nullable=False)
    term_language: Mapped[str] = mapped_column(nullable=False)
    interest_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="interest_by_region_worldwide_records")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_interest_by_region_worldwide_trend_request_id", "trend_request_id"),
        Index("ix_interest_by_region_worldwide_keyword", "keyword"),
        Index("ix_interest_by_region_worldwide_country", "country"),
        Index("ix_interest_by_region_worldwide_country_term_language", "country", "term_language"),
    )
