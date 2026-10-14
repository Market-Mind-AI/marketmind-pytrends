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
        with pytest.raises(DataForSEOClientError, match="not available for Google Ads demand"):
            client._location_name("RU")
        # China is excluded too (Google blocked), with its own reason.
        with pytest.raises(DataForSEOClientError, match="not available for Google Ads demand"):
            client._location_name("CN")

    def test_hebrew_and_chinese_are_sent_in_google_ads_codes(self) -> None:
        """Medido em 14/10/2026: `he` e `zh` recebem 40501 Invalid Field. O
        Google Ads quer `iw`, `zh_CN` e, nos mercados de chinês tradicional,
        `zh_TW`; tudo o mais passa como está."""
        client = DataForSEOClient()
        with patch.object(DataForSEOClient, "_catalogo_de_idiomas", return_value={"iw", "zh_CN", "zh_TW", "pt"}):
            assert client._language_code("he", "IL") == "iw"
            assert client._language_code("zh", "CN") == "zh_CN"
            assert client._language_code("zh", "TW") == "zh_TW"
            assert client._language_code("pt", "BR") == "pt"

    def test_a_language_google_ads_does_not_offer_fails_before_spending(self) -> None:
        client = DataForSEOClient()
        with patch.object(DataForSEOClient, "_catalogo_de_idiomas", return_value={"en"}):
            with pytest.raises(DataForSEOClientError, match="does not offer language 'xx'"):
                client._language_code("xx", "US")

    def test_the_static_language_map_still_answers_when_the_catalogue_cannot(self) -> None:
        client = DataForSEOClient()
        with patch.object(DataForSEOClient, "_catalogo_de_idiomas", return_value=set()):
            assert client._language_code("he", "IL") == "iw"
            assert client._language_code("xx", "US") == "xx"

    def test_a_country_dataforseo_does_not_list_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="does not list country"):
            client._location_name("ZZ")

    def test_a_country_only_the_catalogue_knows_is_resolved(self) -> None:
        """A tabela escrita à mão tinha 25 países. Em 24/09/2026 isso derrubou
        uma análise inteira da Bolívia: `BO` estava no catálogo da DataForSEO e
        no seletor do front, e morria aqui — junto com os outros 125 mercados
        recém-abertos. Quem sabe quais países existem é a fonte."""
        client = DataForSEOClient()
        with patch.object(DataForSEOClient, "_catalogo_de_paises", return_value={"BO": "Bolivia"}):
            assert client._location_name("BO") == "Bolivia"

    def test_the_hand_written_table_still_answers_when_the_catalogue_cannot(self) -> None:
        """Rede de segurança: se a chamada de catálogo não sair, os mercados que
        já funcionavam continuam funcionando."""
        client = DataForSEOClient()
        with patch.object(DataForSEOClient, "_catalogo_de_paises", return_value={}):
            assert client._location_name("BR") == "Brazil"


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

    @patch("app.clients.dataforseo_client.settings")
    @patch("app.clients.dataforseo_client.time.sleep")
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_server_task_error_retries_then_succeeds(
        self,
        mock_api_client_cls: MagicMock,
        mock_keywords_api_cls: MagicMock,
        _mock_sleep: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        # A 5xxxx task code (e.g. 50301 — Google OAuth 503) is transient: the
        # first call fails inside the task body, the retry succeeds.
        mock_settings.default_retries = 3
        mock_settings.default_backoff = 0
        mock_settings.dataforseo_use_sandbox = False
        mock_settings.dataforseo_login = "x"
        mock_settings.dataforseo_password = "y"
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.side_effect = [
            _response_with_results([], status_code=50301),
            _response_with_results([_result_item()]),
        ]
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        records, _ = client.search_volume(["air fryer"], "ES", "en-US")

        assert len(records) == 1
        assert mock_api.google_ads_search_volume_live.call_count == 2

    @patch("app.clients.dataforseo_client.settings")
    @patch("app.clients.dataforseo_client.time.sleep")
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_persistent_server_task_error_exhausts_retries(
        self,
        mock_api_client_cls: MagicMock,
        mock_keywords_api_cls: MagicMock,
        _mock_sleep: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        mock_settings.default_retries = 3
        mock_settings.default_backoff = 0
        mock_settings.dataforseo_use_sandbox = False
        mock_settings.dataforseo_login = "x"
        mock_settings.dataforseo_password = "y"
        mock_api = MagicMock()
        mock_api.google_ads_search_volume_live.return_value = _response_with_results([], status_code=50301)
        _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="after 3 attempts"):
            client.search_volume(["air fryer"], "ES", "en-US")
        assert mock_api.google_ads_search_volume_live.call_count == 3

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
