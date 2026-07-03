import datetime
import uuid
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterestOverTime(Base):
    __tablename__ = "interest_over_time"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    interest_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    is_partial: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, default=datetime.datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="interest_over_time_records")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_interest_over_time_trend_request_id", "trend_request_id"),
        Index("ix_interest_over_time_keyword", "keyword"),
        Index("ix_interest_over_time_country", "country"),
        Index("ix_interest_over_time_date", "date"),
    )
