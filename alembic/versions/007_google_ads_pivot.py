"""Pivot to Google Ads keyword data: add keyword_search_volume + keyword_related,
drop all Google Trends tables.

Revision ID: 007
Revises: 006
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The Google Trends tables retired by this pivot, dropped on upgrade and
# recreated on downgrade. ingestion_runs / trend_requests / raw_api_responses
# are the shared audit scaffolding and are intentionally kept.
_TRENDS_TABLES = (
    "interest_over_time",
    "interest_by_region",
    "interest_by_country",
    "interest_by_region_worldwide",
    "related_queries",
    "related_topics",
    "suggestions",
    "trending_rss",
)


def upgrade() -> None:
    op.create_table(
        "keyword_search_volume",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("search_volume", sa.Numeric(), nullable=True),
        sa.Column("competition", sa.String(), nullable=True),
        sa.Column("competition_index", sa.Integer(), nullable=True),
        sa.Column("cpc", sa.Numeric(), nullable=True),
        sa.Column("monthly_searches", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_keyword_search_volume_trend_request_id", "keyword_search_volume", ["trend_request_id"])
    op.create_index("ix_keyword_search_volume_location_keyword", "keyword_search_volume", ["location", "keyword"])

    op.create_table(
        "keyword_related",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("seed_keyword", sa.String(), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("search_volume", sa.Numeric(), nullable=True),
        sa.Column("competition_index", sa.Integer(), nullable=True),
        sa.Column("cpc", sa.Numeric(), nullable=True),
        sa.Column("monthly_searches", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_keyword_related_trend_request_id", "keyword_related", ["trend_request_id"])
    op.create_index("ix_keyword_related_location_seed_keyword", "keyword_related", ["location", "seed_keyword"])

    for table in _TRENDS_TABLES:
        op.drop_table(table)


def downgrade() -> None:
    op.create_table(
        "interest_over_time",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("interest_value", sa.Numeric(), nullable=False),
        sa.Column("is_partial", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interest_over_time_trend_request_id", "interest_over_time", ["trend_request_id"])
    op.create_index("ix_interest_over_time_keyword", "interest_over_time", ["keyword"])
    op.create_index("ix_interest_over_time_country", "interest_over_time", ["country"])
    op.create_index("ix_interest_over_time_date", "interest_over_time", ["date"])

    op.create_table(
        "interest_by_region",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("interest_value", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interest_by_region_trend_request_id", "interest_by_region", ["trend_request_id"])
    op.create_index("ix_interest_by_region_keyword", "interest_by_region", ["keyword"])
    op.create_index("ix_interest_by_region_country", "interest_by_region", ["country"])
    op.create_index("ix_interest_by_region_region", "interest_by_region", ["region"])

    op.create_table(
        "interest_by_country",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("term", sa.String(), nullable=False, server_default=""),
        sa.Column("term_language", sa.String(), nullable=False, server_default=""),
        sa.Column("interest_value", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interest_by_country_trend_request_id", "interest_by_country", ["trend_request_id"])
    op.create_index("ix_interest_by_country_keyword", "interest_by_country", ["keyword"])
    op.create_index("ix_interest_by_country_country", "interest_by_country", ["country"])
    op.create_index("ix_interest_by_country_term_language", "interest_by_country", ["term_language"])

    op.create_table(
        "interest_by_region_worldwide",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
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

    op.create_table(
        "related_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("query_type", sa.String(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_related_queries_trend_request_id", "related_queries", ["trend_request_id"])
    op.create_index("ix_related_queries_keyword", "related_queries", ["keyword"])
    op.create_index("ix_related_queries_query_type", "related_queries", ["query_type"])

    op.create_table(
        "related_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("topic_type", sa.String(), nullable=False),
        sa.Column("topic_mid", sa.String(), nullable=True),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_related_topics_trend_request_id", "related_topics", ["trend_request_id"])
    op.create_index("ix_related_topics_keyword", "related_topics", ["keyword"])
    op.create_index("ix_related_topics_topic_type", "related_topics", ["topic_type"])

    op.create_table(
        "suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("mid", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_suggestions_trend_request_id", "suggestions", ["trend_request_id"])
    op.create_index("ix_suggestions_keyword", "suggestions", ["keyword"])

    op.create_table(
        "trending_rss",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trend_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trend_requests.id"), nullable=False),
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

    op.drop_table("keyword_related")
    op.drop_table("keyword_search_volume")
