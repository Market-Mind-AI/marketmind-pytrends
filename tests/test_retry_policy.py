"""A política de repetição é a mesma nos quatro coletores (app/utils/retry.py)."""

import pytest

from app.core.config import settings
from app.utils.retry import MAX_BACKOFF_SECONDS, backoff_seconds, is_retryable_status


def test_what_is_retried() -> None:
    assert all(is_retryable_status(s) for s in (408, 429, 500, 502, 503, 504))
    assert not any(is_retryable_status(s) for s in (200, 400, 401, 403, 404, 422, None))


def test_the_wait_doubles_with_jitter_and_has_a_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_backoff", 2)

    assert 2 <= backoff_seconds(1) <= 2.5
    assert 8 <= backoff_seconds(3) <= 10
    assert backoff_seconds(20) == MAX_BACKOFF_SECONDS


def test_retry_after_is_honoured_up_to_the_ceiling() -> None:
    assert backoff_seconds(1, "7") == 7
    assert backoff_seconds(1, "3600") == MAX_BACKOFF_SECONDS


async def test_a_check_is_one_row_per_term_kept_current(mock_session) -> None:  # type: ignore[no-untyped-def]
    """A verificação de um termo é atualizada, não acumulada: uma linha por
    (país, termo em minúsculas)."""
    import uuid

    from sqlalchemy.dialects import postgresql

    from app.repositories.keyword_check_repository import KeywordCheckRepository

    await KeywordCheckRepository(mock_session).record(
        trend_request_id=uuid.uuid4(), location="ES", keywords=["Air Fryer", "air fryer ", "robot"]
    )

    stmt = mock_session.execute.await_args.args[0]
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_keyword_checks_location_keyword DO UPDATE" in sql
    params = stmt.compile(dialect=postgresql.dialect()).params
    assert sorted(v for k, v in params.items() if k.startswith("keyword")) == ["air fryer", "robot"]
