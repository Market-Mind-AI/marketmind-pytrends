import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RelatedTopic(Base):
    __tablename__ = "related_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    topic: Mapped[str] = mapped_column(nullable=False)
    topic_type: Mapped[str] = mapped_column(nullable=False)
    topic_mid: Mapped[str | None] = mapped_column(nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="related_topics")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_related_topics_trend_request_id", "trend_request_id"),
        Index("ix_related_topics_keyword", "keyword"),
        Index("ix_related_topics_topic_type", "topic_type"),
    )
