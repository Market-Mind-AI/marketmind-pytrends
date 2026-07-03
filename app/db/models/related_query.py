import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RelatedQuery(Base):
    __tablename__ = "related_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    query: Mapped[str] = mapped_column(nullable=False)
    query_type: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="related_queries")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_related_queries_trend_request_id", "trend_request_id"),
        Index("ix_related_queries_keyword", "keyword"),
        Index("ix_related_queries_query_type", "query_type"),
    )
