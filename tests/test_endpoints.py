from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import DataForSEORateLimitError, DataForSEOTimeoutError
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


def _override_session(session: AsyncMock) -> None:
    async def gen():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = gen


def _sv_records() -> list[dict]:
    return [
        {
            "keyword": "air fryer",
            "search_volume": 12000,
            "competition": "HIGH",
            "competition_index": 80,
            "cpc": 1.25,
            "monthly_searches": [{"year": 2026, "month": 6, "search_volume": 12000}],
        }
    ]


class TestSearchVolumeEndpoint:
    @patch("app.clients.dataforseo_client.DataForSEOClient.search_volume")
    def test_success(self, mock_client: MagicMock) -> None:
        _override_session(_mock_session())
        mock_client.return_value = (_sv_records(), {"provider": "dataforseo_google_ads"})
        try:
            client = TestClient(app)
            response = client.post(
                "/search-volume",
                json={"location": "ES", "language": "en-US", "keywords": ["air fryer"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["endpoint"] == "search_volume"
            assert data["metadata"]["status"] == "success"
            assert data["metadata"]["records"] == 1
            assert data["metadata"]["provider"] == "Google Ads"
            assert "ingestion_run_id" in data["metadata"]
            assert "trend_request_id" in data["metadata"]
            item = data["data"]["keywords"][0]
            assert item["keyword"] == "air fryer"
            assert item["search_volume"] == 12000
            assert item["monthly_searches"][0]["search_volume"] == 12000
        finally:
            app.dependency_overrides.clear()

    @patch("app.clients.dataforseo_client.DataForSEOClient.search_volume")
    def test_none_fields_success(self, mock_client: MagicMock) -> None:
        _override_session(_mock_session())
        records = [
            {
                "keyword": "obscure kw",
                "search_volume": None,
                "competition": None,
                "competition_index": None,
                "cpc": None,
                "monthly_searches": [],
            }
        ]
        mock_client.return_value = (records, {"provider": "dataforseo_google_ads"})
        try:
            client = TestClient(app)
            response = client.post("/search-volume", json={"location": "ES", "keywords": ["obscure kw"]})
            assert response.status_code == 200
            item = response.json()["data"]["keywords"][0]
            assert item["search_volume"] is None
            assert item["cpc"] is None
            assert item["monthly_searches"] == []
        finally:
            app.dependency_overrides.clear()

    @patch("app.clients.dataforseo_client.DataForSEOClient.search_volume")
    def test_rate_limit_returns_503(self, mock_client: MagicMock) -> None:
        """429 esgotado é a fonte ocupada: 503, como nos outros coletores."""
        _override_session(_mock_session())
        mock_client.side_effect = DataForSEORateLimitError("rate limited")
        try:
            client = TestClient(app)
            response = client.post("/search-volume", json={"location": "ES", "keywords": ["air fryer"]})
            assert response.status_code == 503
        finally:
            app.dependency_overrides.clear()

    @patch("app.clients.dataforseo_client.DataForSEOClient.search_volume")
    def test_timeout_returns_503(self, mock_client: MagicMock) -> None:
        _override_session(_mock_session())
        mock_client.side_effect = DataForSEOTimeoutError("timeout")
        try:
            client = TestClient(app)
            response = client.post("/search-volume", json={"location": "ES", "keywords": ["air fryer"]})
            assert response.status_code == 503
        finally:
            app.dependency_overrides.clear()

    def test_invalid_location_code(self) -> None:
        client = TestClient(app)
        response = client.post("/search-volume", json={"location": "ESP", "keywords": ["air fryer"]})
        assert response.status_code == 422

    def test_missing_keywords(self) -> None:
        client = TestClient(app)
        response = client.post("/search-volume", json={"location": "ES"})
        assert response.status_code == 422


class TestKeywordsForKeywordsEndpoint:
    @patch("app.clients.dataforseo_client.DataForSEOClient.keywords_for_keywords")
    def test_success(self, mock_client: MagicMock) -> None:
        _override_session(_mock_session())
        records = [
            {
                "seed_keyword": "air fryer",
                "keyword": "best air fryer",
                "search_volume": 5000,
                "competition_index": 60,
                "cpc": 0.9,
                "monthly_searches": [{"year": 2026, "month": 6, "search_volume": 5000}],
            }
        ]
        mock_client.return_value = (records, {"provider": "dataforseo_google_ads", "limit": None})
        try:
            client = TestClient(app)
            response = client.post(
                "/keywords-for-keywords",
                json={"location": "ES", "language": "en-US", "seed_keywords": ["air fryer"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["endpoint"] == "keywords_for_keywords"
            assert data["metadata"]["records"] == 1
            item = data["data"]["keywords"][0]
            assert item["seed_keyword"] == "air fryer"
            assert item["keyword"] == "best air fryer"
        finally:
            app.dependency_overrides.clear()

    def test_too_many_seeds_returns_422(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/keywords-for-keywords",
            json={"location": "ES", "seed_keywords": [f"kw{i}" for i in range(21)]},
        )
        assert response.status_code == 422
