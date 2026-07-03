import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrendingRss(Base):
    __tablename__ = "trending_rss"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(nullable=False)
    traffic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pub_date: Mapped[str | None] = mapped_column(nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    articles: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # type: ignore[assignment]
    article_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geo: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="trending_rss_records")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_trending_rss_trend_request_id", "trend_request_id"),
        Index("ix_trending_rss_geo", "geo"),
        Index("ix_trending_rss_title", "title"),
    )
