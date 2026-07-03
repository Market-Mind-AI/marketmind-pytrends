import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str | None] = mapped_column(nullable=True)
    mid: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="suggestions")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_suggestions_trend_request_id", "trend_request_id"),
        Index("ix_suggestions_keyword", "keyword"),
    )
