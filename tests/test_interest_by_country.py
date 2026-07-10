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

_TERMS = [("jamón ibérico", "es"), ("presunto ibérico", "pt"), ("iberico ham", "en")]


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
    def test_multi_term_melt_to_per_term_rows(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        df = pd.DataFrame(
            {
                "jamón ibérico": [80, 5, 2],
                "presunto ibérico": [3, 90, 1],
                "iberico ham": [10, 4, 70],
                "geoCode": ["ES", "PT", "US"],
            },
            index=["Spain", "Portugal", "United States"],
        )
        mock_session.interest_by_region.return_value = df
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        result_df, payload = client.interest_by_country(_TERMS, "today 12-m", "en-US")

        assert payload["provider"] == "pytrends"
        assert payload["terms"] == [{"term": t, "language": lang} for t, lang in _TERMS]
        assert "keyword" not in payload

        # one build_payload with all three term strings, worldwide (geo="")
        mock_session.build_payload.assert_called_once()
        args, kwargs = mock_session.build_payload.call_args
        assert args[0] == ["jamón ibérico", "presunto ibérico", "iberico ham"]
        assert kwargs["geo"] == ""

        records = normalize_interest_by_country(result_df)
        # 3 countries x 3 terms on ONE common axis
        assert len(records) == 9
        assert {"country": "ES", "term": "jamón ibérico", "term_language": "es", "value": 80} in records
        assert {"country": "PT", "term": "presunto ibérico", "term_language": "pt", "value": 90} in records
        assert {"country": "US", "term": "iberico ham", "term_language": "en", "value": 70} in records

    @patch("app.clients.pytrends_client.TrendReq")
    def test_anchor_chaining_merges_onto_one_axis(self, mock_trend_req: MagicMock) -> None:
        terms = [("t0", "en"), ("t1", "en"), ("t2", "en"), ("t3", "en"), ("t4", "en"), ("t5", "en")]
        # batch 1 = t0..t4 ; batch 2 = [t0, t5]. Anchor is t0.
        batch1 = pd.DataFrame(
            {
                "t0": [100, 40],
                "t1": [10, 20],
                "t2": [10, 20],
                "t3": [10, 20],
                "t4": [10, 20],
                "geoCode": ["AA", "BB"],
            },
            index=["A", "B"],
        )
        batch2 = pd.DataFrame(
            {"t0": [50, 10], "t5": [30, 6], "geoCode": ["AA", "BB"]},
            index=["A", "B"],
        )
        mock_session = MagicMock()
        mock_session.interest_by_region.side_effect = [batch1, batch2]
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        result_df, _ = client.interest_by_country(terms, "today 12-m", "en-US")

        assert mock_session.build_payload.call_count == 2
        records = normalize_interest_by_country(result_df)

        # anchor t0 kept only from batch 1 (deduplicated), value unchanged
        t0_rows = [r for r in records if r["term"] == "t0"]
        assert len(t0_rows) == 2
        assert next(r for r in t0_rows if r["country"] == "AA")["value"] == 100

        # factor = ref(100) / batch2 anchor max(50) = 2 -> t5 rescaled onto batch 1 axis
        t5_aa = next(r for r in records if r["term"] == "t5" and r["country"] == "AA")
        assert t5_aa["value"] == 60
        assert t5_aa["term_language"] == "en"

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_by_country_empty(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_by_region.return_value = pd.DataFrame()
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        with pytest.raises(PyTrendsEmptyResponseError):
            client.interest_by_country(_TERMS, "today 12-m", "en-US")


class TestInterestByCountryFallback:
    def test_falls_back_to_dataforseo_when_configured(self) -> None:
        client = PyTrendsClient()
        client._interest_by_country_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]
        mock_dataforseo = MagicMock()
        expected = (pd.DataFrame({"value": [10]}), {"provider": "dataforseo_fallback"})
        mock_dataforseo.interest_by_country.return_value = expected
        client._dataforseo = mock_dataforseo

        _, payload = client.interest_by_country(_TERMS, "today 12-m", "en-US")

        assert payload["provider"] == "dataforseo_fallback"
        mock_dataforseo.interest_by_country.assert_called_once_with(_TERMS, "today 12-m", "en-US")

    def test_no_fallback_configured_propagates_error(self) -> None:
        client = PyTrendsClient()
        client._dataforseo = None
        client._interest_by_country_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]

        with pytest.raises(PyTrendsRateLimitError):
            client.interest_by_country(_TERMS, "today 12-m", "en-US")


class TestDataForSEOInterestByCountry:
    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_worldwide_multi_term_success(
        self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
    ) -> None:
        map_item = GoogleTrendsGoogleTrendsMapElementItem(
            type="google_trends_map",
            data=[
                TrendsMapDataInfo(geo_id="US", geo_name="United States", values=[100.0, 20.0]),
                TrendsMapDataInfo(geo_id="ES", geo_name="Spain", values=[None, 90.0]),
            ],
        )
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([map_item])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        terms = [("air fryer", "en"), ("freidora de aire", "es")]
        client = DataForSEOClient()
        df, payload = client.interest_by_country(terms, "today 12-m", "en-US")

        assert payload["provider"] == "dataforseo_fallback"
        records = normalize_interest_by_country(df)
        assert {"country": "US", "term": "air fryer", "term_language": "en", "value": 100} in records
        assert {"country": "ES", "term": "freidora de aire", "term_language": "es", "value": 90} in records
        # null coerced to 0
        assert {"country": "ES", "term": "air fryer", "term_language": "en", "value": 0} in records

    @patch("app.clients.dataforseo_client.KeywordsDataApi")
    @patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
    def test_no_map_data_raises(self, mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.google_trends_explore_live.return_value = _response_with_items([])
        mock_keywords_api_cls.return_value = mock_api
        mock_api_client_cls.return_value.__enter__.return_value = MagicMock()

        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError):
            client.interest_by_country([("air fryer", "en")], "today 12-m", "en-US")


class TestNormalizeInterestByCountry:
    def test_long_rows_pass_through(self) -> None:
        df = pd.DataFrame(
            {
                "country": ["ES", "PT"],
                "term": ["jamón ibérico", "presunto ibérico"],
                "term_language": ["es", "pt"],
                "value": [82, 40],
            }
        )
        result = normalize_interest_by_country(df)
        assert result[0] == {"country": "ES", "term": "jamón ibérico", "term_language": "es", "value": 82}
        assert result[1] == {"country": "PT", "term": "presunto ibérico", "term_language": "pt", "value": 40}

    def test_nan_value_becomes_zero(self) -> None:
        df = pd.DataFrame({"country": ["FR"], "term": ["four à air"], "term_language": ["fr"], "value": [float("nan")]})
        result = normalize_interest_by_country(df)
        assert result[0]["value"] == 0

    def test_empty_dataframe(self) -> None:
        result = normalize_interest_by_country(pd.DataFrame())
        assert result == []
