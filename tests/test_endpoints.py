from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from app.core.exceptions import PyTrendsEmptyResponseError, PyTrendsTimeoutError
from app.db.session import get_session
from app.main import app


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session


def _mock_interest_over_time_df() -> pd.DataFrame:
    index = pd.to_datetime(["2025-01-01", "2025-02-01"])
    return pd.DataFrame(
        {"air fryer": [50, 75], "isPartial": [False, False]},
        index=index,
    )


class TestInterestOverTimeEndpoint:
    @patch("app.clients.pytrends_client.PyTrendsClient.interest_over_time")
    def test_success(self, mock_client: MagicMock) -> None:
        session = _mock_session()

        async def override_session():  # type: ignore[no-untyped-def]
            yield session

        app.dependency_overrides[get_session] = override_session

        df = _mock_interest_over_time_df()
        req_payload = {
            "keyword": "air fryer",
            "country": "ES",
            "timeframe": "today 12-m",
            "language": "en-US",
        }
        mock_client.return_value = (df, req_payload)

        try:
            client = TestClient(app)
            response = client.post(
                "/interest-over-time",
                json={"keyword": "air fryer", "country": "ES", "timeframe": "today 12-m", "language": "en-US"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["endpoint"] == "interest_over_time"
            assert data["metadata"]["status"] == "success"
            assert data["metadata"]["records"] == 2
            assert data["metadata"]["stored"] is True
            assert "ingestion_run_id" in data["metadata"]
            assert "trend_request_id" in data["metadata"]
            assert len(data["data"]["interest_over_time"]) == 2
        finally:
            app.dependency_overrides.clear()

    @patch("app.clients.pytrends_client.PyTrendsClient.interest_over_time")
    def test_empty_response(self, mock_client: MagicMock) -> None:
        session = _mock_session()

        async def override_session():  # type: ignore[no-untyped-def]
            yield session

        app.dependency_overrides[get_session] = override_session
        mock_client.side_effect = PyTrendsEmptyResponseError("No data returned")

        try:
            client = TestClient(app)
            response = client.post(
                "/interest-over-time",
                json={"keyword": "xyz123abc", "country": "ES"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @patch("app.clients.pytrends_client.PyTrendsClient.interest_over_time")
    def test_timeout(self, mock_client: MagicMock) -> None:
        session = _mock_session()

        async def override_session():  # type: ignore[no-untyped-def]
            yield session

        app.dependency_overrides[get_session] = override_session
        mock_client.side_effect = PyTrendsTimeoutError("Timeout")

        try:
            client = TestClient(app)
            response = client.post(
                "/interest-over-time",
                json={"keyword": "air fryer", "country": "ES"},
            )
            assert response.status_code == 504
        finally:
            app.dependency_overrides.clear()

    def test_invalid_request_missing_keyword(self) -> None:
        client = TestClient(app)
        response = client.post("/interest-over-time", json={"country": "ES"})
        assert response.status_code == 422

    def test_invalid_country_code(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/interest-over-time",
            json={"keyword": "air fryer", "country": "ESP"},
        )
        assert response.status_code == 422


class TestSuggestionsEndpoint:
    @patch("app.clients.pytrends_client.PyTrendsClient.suggestions")
    def test_success(self, mock_client: MagicMock) -> None:
        session = _mock_session()

        async def override_session():  # type: ignore[no-untyped-def]
            yield session

        app.dependency_overrides[get_session] = override_session
        mock_client.return_value = (
            [{"title": "Air fryer", "type": "Topic", "mid": "/m/abc"}],
            {"keyword": "air fryer", "language": "en-US"},
        )

        try:
            client = TestClient(app)
            response = client.post("/suggestions", json={"keyword": "air fryer"})

            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["endpoint"] == "suggestions"
            assert len(data["data"]["suggestions"]) == 1
            assert data["data"]["suggestions"][0]["title"] == "Air fryer"
        finally:
            app.dependency_overrides.clear()
