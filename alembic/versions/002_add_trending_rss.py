"""Add trending_rss table

Revision ID: 002
Revises: 001
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trending_rss",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("traffic", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pub_date", sa.String(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("articles", postgresql.JSONB(), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=True),
        sa.Column("geo", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trending_rss_trend_request_id", "trending_rss", ["trend_request_id"])
    op.create_index("ix_trending_rss_geo", "trending_rss", ["geo"])
    op.create_index("ix_trending_rss_title", "trending_rss", ["title"])


def downgrade() -> None:
    op.drop_table("trending_rss")
