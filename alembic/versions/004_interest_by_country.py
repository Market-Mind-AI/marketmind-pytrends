"""Add interest_by_country table

Revision ID: 004
Revises: 003
Create Date: 2026-07-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interest_by_country",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("interest_value", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interest_by_country_trend_request_id", "interest_by_country", ["trend_request_id"])
    op.create_index("ix_interest_by_country_keyword", "interest_by_country", ["keyword"])
    op.create_index("ix_interest_by_country_country", "interest_by_country", ["country"])


def downgrade() -> None:
    op.drop_table("interest_by_country")
