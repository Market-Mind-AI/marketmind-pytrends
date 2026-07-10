from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from dataforseo_client.models.google_trends_google_trends_map_element_item import (
    GoogleTrendsGoogleTrendsMapElementItem,
)
from dataforseo_client.models.trends_map_data_info import TrendsMapDataInfo

from app.clients.dataforseo_client import DataForSEOClient
from app.clients.pytrends_client import PyTrendsClient
from app.core.exceptions import DataForSEOClientError, PyTrendsEmptyResponseError, PyTrendsRateLimitError
from app.utils.normalization import normalize_interest_by_country


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


class TestPyTrendsInterestByCountry:
    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_by_country_success(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        df = pd.DataFrame(
            {"test": [100, 60], "geoCode": ["US", "ES"]},
            index=["United States", "Spain"],
        )
        mock_session.interest_by_region.return_value = df
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        result_df, payload = client.interest_by_country("test", "today 12-m", "en-US")

        assert not result_df.empty
        assert payload["keyword"] == "test"
        assert payload["provider"] == "pytrends"
        assert "country" not in payload
        # worldwide => empty geo
        mock_session.build_payload.assert_called_once()
        _, kwargs = mock_session.build_payload.call_args
        assert kwargs["geo"] == ""
        mock_session.interest_by_region.assert_called_once_with(
            resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True
        )

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_by_country_empty(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_by_region.return_value = pd.DataFrame()
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        with pytest.raises(PyTrendsEmptyResponseError):
            client.interest_by_country("test", "today 12-m", "en-US")


class TestInterestByCountryFallback:
    def test_falls_back_to_dataforseo_when_configured(self) -> None:
        client = PyTrendsClient()
        client._interest_by_country_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]
        mock_dataforseo = MagicMock()
        expected = (pd.DataFrame({"test": [10]}), {"provider": "dataforseo_fallback"})
        mock_dataforseo.interest_by_country.return_value = expected
        client._dataforseo = mock_dataforseo

        _, payload = client.interest_by_country("test", "today 12-m", "en-US")

        assert payload["provider"] == "dataforseo_fallback"
        mock_dataforseo.interest_by_country.assert_called_once_with("test", "today 12-m", "en-US")

    def test_no_fallback_configured_propagates_error(self) -> None:
        client = PyTrendsClient()
        client._dataforseo = None
        client._interest_by_country_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]

        with pytest.raises(PyTrendsRateLimitError):
            client.interest_by_country("test", "today 12-m", "en-US")


class TestDataForSEOInterestByCountry:
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_worldwide_success(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        map_item = GoogleTrendsGoogleTrendsMapElementItem(
            type="google_trends_map",
            data=[
                TrendsMapDataInfo(geo_id="US", geo_name="United States", values=[100.0]),
                TrendsMapDataInfo(geo_id="ES", geo_name="Spain", values=[None]),
            ],
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([map_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        df, payload = client.interest_by_country("air fryer", "today 12-m", "en-US")

        assert payload["provider"] == "dataforseo_fallback"
        records = normalize_interest_by_country(df, "air fryer")
        assert {"country": "US", "value": 100} in records
        assert {"country": "ES", "value": 0} in records

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_no_map_data_raises(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError):
            client.interest_by_country("air fryer", "today 12-m", "en-US")


class TestNormalizeInterestByCountry:
    def test_prefers_geo_code(self) -> None:
        df = pd.DataFrame(
            {"air fryer": [100, 60], "geoCode": ["US", "ES"]},
            index=["United States", "Spain"],
        )
        result = normalize_interest_by_country(df, "air fryer")
        assert len(result) == 2
        assert result[0] == {"country": "US", "value": 100}
        assert result[1] == {"country": "ES", "value": 60}

    def test_falls_back_to_index_when_no_geo_code(self) -> None:
        df = pd.DataFrame({"air fryer": [82, 40]}, index=["Spain", "France"])
        result = normalize_interest_by_country(df, "air fryer")
        assert result[0] == {"country": "Spain", "value": 82}

    def test_none_value_becomes_zero(self) -> None:
        df = pd.DataFrame(
            {"air fryer": [float("nan")], "geoCode": ["FR"]},
            index=["France"],
        )
        result = normalize_interest_by_country(df, "air fryer")
        assert result[0]["value"] == 0

    def test_empty_dataframe(self) -> None:
        result = normalize_interest_by_country(pd.DataFrame(), "air fryer")
        assert result == []
