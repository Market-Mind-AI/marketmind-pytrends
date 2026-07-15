from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from dataforseo_client.rest import ApiException

from app.clients.dataforseo_client import DataForSEOClient
from app.core.exceptions import (
    DataForSEOClientError,
    DataForSEORateLimitError,
    DataForSEOTimeoutError,
)


def _result_item(**kwargs: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "keyword": "air fryer",
        "search_volume": 12000,
        "competition": "HIGH",
        "competition_index": 80,
        "cpc": 1.25,
        "monthly_searches": [SimpleNamespace(year=2026, month=6, search_volume=12000)],
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _response_with_results(results: list[object], status_code: int = 20000) -> MagicMock:
    task = MagicMock()
    task.status_code = status_code
    task.status_message = "Ok."
    task.result = results
    response = MagicMock()
    response.tasks = [task]
    return response


def _install_api(mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock, mock_api: MagicMock) -> None:
    mock_keywords_api_cls.return_value = mock_api
    mock_api_client_cls.return_value.__enter__.return_value = MagicMock()


class TestDataForSEOClientLocations:
    def test_unsupported_country_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="sanctioned"):
            client._location_name("RU")

    def test_unmapped_country_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="No DataForSEO location_name mapping"):
            client._location_name("ZZ")


class TestSearchVolume:
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_success(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.return_value = _response_with_results([_result_item()])
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        records, payload = client.search_volume(["air fryer"], "ES", "en-US")

        assert len(records) == 1
        rec = records[0]
        assert rec["keyword"] == "air fryer"
        assert rec["search_volume"] == 12000
        assert rec["competition"] == "HIGH"
        assert rec["competition_index"] == 80
        assert rec["cpc"] == 1.25
        assert rec["monthly_searches"] == [{"year": 2026, "month": 6, "search_volume": 12000}]
        assert payload["provider"] == "dataforseo_google_ads"
        assert payload["location_name"] == "Spain"
        assert payload["language_code"] == "en-US"

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_none_numeric_fields_are_coerced_gracefully(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        item = _result_item(
            search_volume=None, competition=None, competition_index=None, cpc=None, monthly_searches=None
        )
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.return_value = _response_with_results([item])
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        records, _ = client.search_volume(["air fryer"], "ES", "en-US")

        rec = records[0]
        assert rec["search_volume"] is None
        assert rec["competition"] is None
        assert rec["competition_index"] is None
        assert rec["cpc"] is None
        assert rec["monthly_searches"] == []

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_task_error_raises(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.return_value = _response_with_results([], status_code=40501)
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="DataForSEO task failed"):
            client.search_volume(["air fryer"], "ES", "en-US")

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_rate_limit_maps_to_rate_limit_error(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.side_effect = ApiException(status=429, reason="Too Many Requests")
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        with pytest.raises(DataForSEORateLimitError):
            client.search_volume(["air fryer"], "ES", "en-US")

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_timeout_maps_to_timeout_error(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.side_effect = ApiException(status=504, reason="Gateway Timeout")
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        with pytest.raises(DataForSEOTimeoutError):
            client.search_volume(["air fryer"], "ES", "en-US")

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_generic_api_error_maps_to_client_error(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.side_effect = ApiException(status=500, reason="Server Error")
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError):
            client.search_volume(["air fryer"], "ES", "en-US")


class TestKeywordsForKeywords:
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_success_adds_seed_and_respects_limit(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        results = [
            _result_item(keyword="air fryer recipes"),
            _result_item(keyword="best air fryer"),
            _result_item(keyword="air fryer oven"),
        ]
        mock_api = MagicMock()
        mock_api.google_ads_keywords_for_keywords_live.return_value = _response_with_results(results)
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        records, payload = client.keywords_for_keywords(["air fryer"], "ES", "en-US", limit=2)

        assert len(records) == 2
        assert all(r["seed_keyword"] == "air fryer" for r in records)
        assert records[0]["keyword"] == "air fryer recipes"
        assert payload["provider"] == "dataforseo_google_ads"
        assert payload["limit"] == 2

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_no_limit_returns_all(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        results = [_result_item(keyword="a"), _result_item(keyword="b")]
        mock_api = MagicMock()
        mock_api.google_ads_keywords_for_keywords_live.return_value = _response_with_results(results)
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        records, _ = client.keywords_for_keywords(["air fryer"], "ES", "en-US", limit=None)
        assert len(records) == 2
