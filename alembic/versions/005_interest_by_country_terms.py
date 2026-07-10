"""Add localized term columns to interest_by_country

Revision ID: 005
Revises: 004
Create Date: 2026-07-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interest_by_country",
        sa.Column("term", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "interest_by_country",
        sa.Column("term_language", sa.String(), nullable=False, server_default=""),
    )
    op.create_index("ix_interest_by_country_term_language", "interest_by_country", ["term_language"])


def downgrade() -> None:
    op.drop_index("ix_interest_by_country_term_language", table_name="interest_by_country")
    op.drop_column("interest_by_country", "term_language")
    op.drop_column("interest_by_country", "term")
