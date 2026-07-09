from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from dataforseo_client.models.google_trends_google_trends_graph_element_item import (
    GoogleTrendsGoogleTrendsGraphElementItem,
)
from dataforseo_client.models.google_trends_google_trends_map_element_item import (
    GoogleTrendsGoogleTrendsMapElementItem,
)
from dataforseo_client.models.google_trends_google_trends_queries_list_element_item import (
    GoogleTrendsGoogleTrendsQueriesListElementItem,
)
from dataforseo_client.models.list_data_info import ListDataInfo
from dataforseo_client.models.trends_graph_data_info import TrendsGraphDataInfo
from dataforseo_client.models.trends_map_data_info import TrendsMapDataInfo

from app.clients.dataforseo_client import DataForSEOClient, _timeframe_to_date_range
from app.core.exceptions import DataForSEOClientError


def _response_with_items(items: list[object]) -> MagicMock:
    result_item = MagicMock()
    result_item.items = items
    task = MagicMock()
    task.status_code = 20000
    task.status_message = "Ok."
    task.result = [result_item]
    response = MagicMock()
    response.tasks = [task]
    return response


class TestTimeframeToDateRange:
    def test_months(self) -> None:
        date_from, date_to = _timeframe_to_date_range("today 12-m")
        today = datetime.now(UTC).date()
        assert date_to == today.isoformat()
        assert date_from == (today - timedelta(days=360)).isoformat()

    def test_years(self) -> None:
        date_from, date_to = _timeframe_to_date_range("today 5-y")
        today = datetime.now(UTC).date()
        assert date_from == (today - timedelta(days=5 * 365)).isoformat()

    def test_unrecognized_defaults_to_12_months(self) -> None:
        date_from, date_to = _timeframe_to_date_range("some weird string")
        today = datetime.now(UTC).date()
        assert date_from == (today - timedelta(days=365)).isoformat()
        assert date_to == today.isoformat()


class TestDataForSEOClientLocations:
    def test_unsupported_country_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="sanctioned"):
            client._location_name("RU")

    def test_unmapped_country_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="No DataForSEO location_name mapping"):
            client._location_name("ZZ")


class TestDataForSEOClientExplore:
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_interest_over_time_success(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        graph_item = GoogleTrendsGoogleTrendsGraphElementItem(
            type="google_trends_graph",
            data=[TrendsGraphDataInfo(date_from="2026-01-01", date_to="2026-01-07", values=[42.0], missing_data=False)],
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([graph_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        df, payload = client.interest_over_time("air fryer", "US", "today 12-m", "en-US")

        assert not df.empty
        assert df["air fryer"].iloc[0] == 42.0
        assert payload["provider"] == "dataforseo_fallback"

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_interest_by_region_success(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        map_item = GoogleTrendsGoogleTrendsMapElementItem(
            type="google_trends_map",
            data=[TrendsMapDataInfo(geo_id="US-NY", geo_name="New York", values=[77.0])],
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([map_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        df, payload = client.interest_by_region("air fryer", "US", "today 12-m", "en-US")

        assert not df.empty
        assert df.loc["New York", "air fryer"] == 77.0
        assert payload["provider"] == "dataforseo_fallback"

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_null_region_value_becomes_zero_not_nan(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        # DataForSEO reports no-data regions (e.g. Ceuta) with a null value;
        # it must become 0.0, never NaN — a NaN later fails JSON persistence
        # ("invalid input syntax for type json: Token NaN"). Regression test
        # for the live-mode bug found 2026-07-09.
        map_item = GoogleTrendsGoogleTrendsMapElementItem(
            type="google_trends_map",
            data=[
                TrendsMapDataInfo(geo_id="ES-EX", geo_name="Extremadura", values=[100.0]),
                TrendsMapDataInfo(geo_id="ES-CE", geo_name="Ceuta", values=[None]),
            ],
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([map_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        df, _ = client.interest_by_region("jamon iberico", "ES", "today 12-m", "es")

        assert df.loc["Ceuta", "jamon iberico"] == 0.0
        assert not df["jamon iberico"].isna().any()

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_related_queries_success(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        queries_item = GoogleTrendsGoogleTrendsQueriesListElementItem(
            type="google_trends_queries_list",
            data=ListDataInfo(
                top=[{"query": "best air fryer", "value": 100}],
                rising=[{"query": "air fryer sale", "value": 250}],
            ),
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([queries_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        data, payload = client.related_queries("air fryer", "US", "today 12-m", "en-US")

        assert data["air fryer"]["top"].iloc[0]["query"] == "best air fryer"
        assert data["air fryer"]["rising"].iloc[0]["value"] == 250
        assert payload["provider"] == "dataforseo_fallback"

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_task_error_raises(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        task = MagicMock()
        task.status_code = 40001
        task.status_message = "Auth error."
        task.result = None
        response = MagicMock()
        response.tasks = [task]

        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = response
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError, match="DataForSEO task failed"):
            client.interest_over_time("air fryer", "US", "today 12-m", "en-US")
