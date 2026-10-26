import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KeywordCheck(Base):
    """A última vez que a DataForSEO respondeu sobre um termo num país.

    É a "verificação" dos outros coletores, trazida para cá: a pergunta "quando
    olhamos isto pela última vez?" separada de "o que voltou". Uma resposta sem
    linha para o termo -- o Google Ads não tem volume para ele -- também é
    resposta, e sem este registro o termo ficava "faltando" para sempre e era
    cobrado de novo a cada análise.

    Uma linha por (país, termo em minúsculas), atualizada a cada coleta que
    respondeu.
    """

    __tablename__ = "keyword_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location: Mapped[str] = mapped_column(nullable=False)
    keyword: Mapped[str] = mapped_column(nullable=False)
    trend_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trend_requests.id"), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (UniqueConstraint("location", "keyword", name="uq_keyword_checks_location_keyword"),)
