from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.trend_request_repository import TrendRequestRepository


class TestIngestionRunRepository:
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        repo = IngestionRunRepository(session)
        run = await repo.create(source="dataforseo_google_ads", request_payload={"keyword": "test"})

        assert run.source == "dataforseo_google_ads"
        assert run.status == "running"
        assert run.request_payload == {"keyword": "test"}
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_success(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        repo = IngestionRunRepository(session)
        run = await repo.create(source="dataforseo_google_ads", request_payload={"keyword": "test"})
        updated = await repo.mark_success(run, execution_time_ms=500)

        assert updated.status == "success"
        assert updated.execution_time_ms == 500
        assert updated.finished_at is not None

    @pytest.mark.asyncio
    async def test_mark_failed(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        repo = IngestionRunRepository(session)
        run = await repo.create(source="dataforseo_google_ads", request_payload={"keyword": "test"})
        updated = await repo.mark_failed(run, error_message="Timeout", execution_time_ms=3000)

        assert updated.status == "failed"
        assert updated.error_message == "Timeout"
        assert updated.execution_time_ms == 3000


class TestTrendRequestRepository:
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        repo = TrendRequestRepository(session)
        run_id = uuid4()
        tr = await repo.create(
            ingestion_run_id=run_id,
            keyword="air fryer",
            country="ES",
            endpoint="search_volume",
            language="en-US",
        )

        assert tr.keyword == "air fryer"
        assert tr.country == "ES"
        assert tr.endpoint == "search_volume"
        assert tr.ingestion_run_id == run_id
        session.add.assert_called_once()
