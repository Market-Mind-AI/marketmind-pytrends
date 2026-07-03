"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ingestion_runs_source", "ingestion_runs", ["source"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])

    op.create_table(
        "trend_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.id"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trend_requests_keyword", "trend_requests", ["keyword"])
    op.create_index("ix_trend_requests_country", "trend_requests", ["country"])
    op.create_index("ix_trend_requests_endpoint", "trend_requests", ["endpoint"])
    op.create_index("ix_trend_requests_ingestion_run_id", "trend_requests", ["ingestion_run_id"])

    op.create_table(
        "raw_api_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_api_responses_trend_request_id", "raw_api_responses", ["trend_request_id"])
    op.create_index("ix_raw_api_responses_endpoint", "raw_api_responses", ["endpoint"])

    op.create_table(
        "interest_over_time",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
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
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
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
        "related_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
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
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
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
        sa.Column(
            "trend_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trend_requests.id"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("mid", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_suggestions_trend_request_id", "suggestions", ["trend_request_id"])
    op.create_index("ix_suggestions_keyword", "suggestions", ["keyword"])


def downgrade() -> None:
    op.drop_table("suggestions")
    op.drop_table("related_topics")
    op.drop_table("related_queries")
    op.drop_table("interest_by_region")
    op.drop_table("interest_over_time")
    op.drop_table("raw_api_responses")
    op.drop_table("trend_requests")
    op.drop_table("ingestion_runs")
