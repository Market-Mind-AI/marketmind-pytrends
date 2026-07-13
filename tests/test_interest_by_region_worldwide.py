from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.clients.dataforseo_client import DataForSEOClient
from app.clients.pytrends_client import PyTrendsClient
from app.core.exceptions import DataForSEOClientError, PyTrendsEmptyResponseError, PyTrendsRateLimitError
from app.utils.normalization import normalize_interest_by_region_worldwide

_TERMS = [("jamón ibérico", "es"), ("presunto ibérico", "pt"), ("iberico ham", "en")]


class TestPyTrendsInterestByRegionWorldwide:
    @patch("app.clients.pytrends_client.TrendReq")
    def test_multi_term_melt_derives_country_and_drops_national_rows(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        # Two true sub-regions (ES-MD, US-CA) plus one national/aggregate row (ES,
        # no hyphen) that MUST be dropped.
        df = pd.DataFrame(
            {
                "jamón ibérico": [80, 2, 50],
                "presunto ibérico": [3, 1, 5],
                "iberico ham": [10, 70, 8],
                "geoCode": ["ES-MD", "US-CA", "ES"],
            },
            index=["Madrid", "California", "Spain"],
        )
        mock_session.interest_by_region.return_value = df
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        result_df, payload = client.interest_by_region_worldwide(_TERMS, "today 12-m", "en-US")

        assert payload["provider"] == "pytrends"
        assert payload["terms"] == [{"term": t, "language": lang} for t, lang in _TERMS]
        assert "keyword" not in payload

        # one build_payload with all three term strings, worldwide (geo="")
        mock_session.build_payload.assert_called_once()
        args, kwargs = mock_session.build_payload.call_args
        assert args[0] == ["jamón ibérico", "presunto ibérico", "iberico ham"]
        assert kwargs["geo"] == ""
        # sub-national resolution requested with geo codes
        _, region_kwargs = mock_session.interest_by_region.call_args
        assert region_kwargs["resolution"] == "REGION"
        assert region_kwargs["inc_geo_code"] is True

        records = normalize_interest_by_region_worldwide(result_df)
        # 2 sub-regions x 3 terms (national "ES" row dropped)
        assert len(records) == 6
        assert all(r["region_code"] != "ES" for r in records)
        assert {
            "country": "ES",
            "region_code": "ES-MD",
            "region_name": "Madrid",
            "term": "jamón ibérico",
            "term_language": "es",
            "value": 80,
        } in records
        assert {
            "country": "US",
            "region_code": "US-CA",
            "region_name": "California",
            "term": "iberico ham",
            "term_language": "en",
            "value": 70,
        } in records

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
                "geoCode": ["US-CA", "US-NY"],
            },
            index=["California", "New York"],
        )
        batch2 = pd.DataFrame(
            {"t0": [50, 10], "t5": [30, 6], "geoCode": ["US-CA", "US-NY"]},
            index=["California", "New York"],
        )
        mock_session = MagicMock()
        mock_session.interest_by_region.side_effect = [batch1, batch2]
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        result_df, _ = client.interest_by_region_worldwide(terms, "today 12-m", "en-US")

        assert mock_session.build_payload.call_count == 2
        records = normalize_interest_by_region_worldwide(result_df)

        # anchor t0 kept only from batch 1 (deduplicated), value unchanged
        t0_rows = [r for r in records if r["term"] == "t0"]
        assert len(t0_rows) == 2
        ca_t0 = next(r for r in t0_rows if r["region_code"] == "US-CA")
        assert ca_t0["value"] == 100
        assert ca_t0["country"] == "US"

        # factor = ref(100) / batch2 anchor max(50) = 2 -> t5 rescaled onto batch 1 axis
        t5_ca = next(r for r in records if r["term"] == "t5" and r["region_code"] == "US-CA")
        assert t5_ca["value"] == 60
        assert t5_ca["term_language"] == "en"

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_by_region_worldwide_empty(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_by_region.return_value = pd.DataFrame()
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        with pytest.raises(PyTrendsEmptyResponseError):
            client.interest_by_region_worldwide(_TERMS, "today 12-m", "en-US")


class TestInterestByRegionWorldwideFallback:
    def test_falls_back_to_dataforseo_which_cannot_do_it(self) -> None:
        # PyTrends exhausts retries; the DataForSEO fallback is configured but
        # cannot produce worldwide sub-regions, so it raises DataForSEOClientError.
        client = PyTrendsClient()
        client._interest_by_region_worldwide_pytrends = MagicMock(  # type: ignore[method-assign]
            side_effect=PyTrendsRateLimitError("rate limited")
        )
        client._dataforseo = DataForSEOClient()

        with pytest.raises(DataForSEOClientError):
            client.interest_by_region_worldwide(_TERMS, "today 12-m", "en-US")

    def test_no_fallback_configured_propagates_error(self) -> None:
        client = PyTrendsClient()
        client._dataforseo = None
        client._interest_by_region_worldwide_pytrends = MagicMock(  # type: ignore[method-assign]
            side_effect=PyTrendsRateLimitError("rate limited")
        )

        with pytest.raises(PyTrendsRateLimitError):
            client.interest_by_region_worldwide(_TERMS, "today 12-m", "en-US")


class TestDataForSEOInterestByRegionWorldwide:
    def test_cannot_provide_worldwide_subregions_raises(self) -> None:
        client = DataForSEOClient()
        with pytest.raises(DataForSEOClientError):
            client.interest_by_region_worldwide(_TERMS, "today 12-m", "en-US")


class TestNormalizeInterestByRegionWorldwide:
    def test_long_rows_pass_through(self) -> None:
        df = pd.DataFrame(
            {
                "country": ["ES", "PT"],
                "region_code": ["ES-MD", "PT-11"],
                "region_name": ["Madrid", "Lisboa"],
                "term": ["jamón ibérico", "presunto ibérico"],
                "term_language": ["es", "pt"],
                "value": [82, 40],
            }
        )
        result = normalize_interest_by_region_worldwide(df)
        assert result[0] == {
            "country": "ES",
            "region_code": "ES-MD",
            "region_name": "Madrid",
            "term": "jamón ibérico",
            "term_language": "es",
            "value": 82,
        }

    def test_nan_value_becomes_zero(self) -> None:
        df = pd.DataFrame(
            {
                "country": ["FR"],
                "region_code": ["FR-IDF"],
                "region_name": ["Île-de-France"],
                "term": ["four à air"],
                "term_language": ["fr"],
                "value": [float("nan")],
            }
        )
        result = normalize_interest_by_region_worldwide(df)
        assert result[0]["value"] == 0

    def test_missing_region_name_stays_none(self) -> None:
        df = pd.DataFrame(
            {
                "country": ["FR"],
                "region_code": ["FR-IDF"],
                "region_name": [None],
                "term": ["four à air"],
                "term_language": ["fr"],
                "value": [10],
            }
        )
        result = normalize_interest_by_region_worldwide(df)
        assert result[0]["region_name"] is None

    def test_empty_dataframe(self) -> None:
        result = normalize_interest_by_region_worldwide(pd.DataFrame())
        assert result == []
