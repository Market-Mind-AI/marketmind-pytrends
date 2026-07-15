import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KeywordRelated(Base):
    __tablename__ = "keyword_related"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    seed_keyword: Mapped[str] = mapped_column(nullable=False)
    keyword: Mapped[str] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)
    language: Mapped[str] = mapped_column(nullable=False)
    search_volume: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    competition_index: Mapped[int | None] = mapped_column(nullable=True)
    cpc: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    monthly_searches: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # type: ignore[type-arg]
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="keyword_related_records")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_keyword_related_trend_request_id", "trend_request_id"),
        Index("ix_keyword_related_location_seed_keyword", "location", "seed_keyword"),
    )
