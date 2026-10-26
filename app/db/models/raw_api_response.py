import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.time import utc_now


class RawApiResponse(Base):
    __tablename__ = "raw_api_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[assignment]
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[assignment]
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)

    trend_request: Mapped["TrendRequest"] = relationship(back_populates="raw_api_responses")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_raw_api_responses_trend_request_id", "trend_request_id"),
        Index("ix_raw_api_responses_endpoint", "endpoint"),
    )
