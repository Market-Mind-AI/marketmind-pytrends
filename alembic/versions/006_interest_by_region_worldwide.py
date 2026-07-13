"""Add interest_by_region_worldwide table

Revision ID: 006
Revises: 005
Create Date: 2026-07-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interest_by_region_worldwide",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("region_code", sa.String(), nullable=False),
        sa.Column("region_name", sa.String(), nullable=True),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("term_language", sa.String(), nullable=False),
        sa.Column("interest_value", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_interest_by_region_worldwide_trend_request_id", "interest_by_region_worldwide", ["trend_request_id"]
    )
    op.create_index("ix_interest_by_region_worldwide_keyword", "interest_by_region_worldwide", ["keyword"])
    op.create_index("ix_interest_by_region_worldwide_country", "interest_by_region_worldwide", ["country"])
    op.create_index(
        "ix_interest_by_region_worldwide_country_term_language",
        "interest_by_region_worldwide",
        ["country", "term_language"],
    )


def downgrade() -> None:
    op.drop_index("ix_interest_by_region_worldwide_country_term_language", table_name="interest_by_region_worldwide")
    op.drop_index("ix_interest_by_region_worldwide_country", table_name="interest_by_region_worldwide")
    op.drop_index("ix_interest_by_region_worldwide_keyword", table_name="interest_by_region_worldwide")
    op.drop_index("ix_interest_by_region_worldwide_trend_request_id", table_name="interest_by_region_worldwide")
    op.drop_table("interest_by_region_worldwide")
