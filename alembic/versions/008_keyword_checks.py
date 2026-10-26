"""keyword_checks: a "no data" answer from Google Ads counts as checked

Um termo para o qual o Google Ads não tem volume volta sem linha, e o frescor
deste serviço era lido das linhas guardadas: o termo ficava "faltando" para
sempre e era cobrado de novo a cada análise. A verificação passa a ser
registrada à parte, por (país, termo), sempre que a DataForSEO responde -- a
mesma regra de verificação dos outros coletores.

O que já foi coletado entra como verificado na data da coleta mais recente,
para que nada que hoje conta como fresco passe a contar como faltando.

Revision ID: 008
Revises: 007
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "keyword_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("location", "keyword", name="uq_keyword_checks_location_keyword"),
    )
    op.execute(
        """
        INSERT INTO keyword_checks (id, location, keyword, trend_request_id, checked_at)
        SELECT DISTINCT ON (location, lower(keyword))
               gen_random_uuid(), location, lower(keyword), trend_request_id, created_at
        FROM keyword_search_volume
        ORDER BY location, lower(keyword), created_at DESC
        """
    )


def downgrade() -> None:
    op.drop_table("keyword_checks")
