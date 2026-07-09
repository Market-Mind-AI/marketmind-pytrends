from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from requests.exceptions import Timeout

from app.clients.pytrends_client import PyTrendsClient
from app.core.exceptions import PyTrendsEmptyResponseError, PyTrendsRateLimitError, PyTrendsTimeoutError


class TestPyTrendsClient:
    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_over_time_success(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        index = pd.to_datetime(["2025-01-01"])
        mock_session.interest_over_time.return_value = pd.DataFrame({"test": [50], "isPartial": [False]}, index=index)
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        df, payload = client.interest_over_time("test", "US", "today 12-m", "en-US")

        assert not df.empty
        assert payload["keyword"] == "test"
        mock_session.build_payload.assert_called_once()

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_over_time_empty(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_over_time.return_value = pd.DataFrame()
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        with pytest.raises(PyTrendsEmptyResponseError):
            client.interest_over_time("test", "US", "today 12-m", "en-US")

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_over_time_timeout(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_over_time.side_effect = Timeout("Connection timed out")
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        client._dataforseo = None  # isolate PyTrends error behavior from the fallback (env may have creds)
        fn = client._interest_over_time_pytrends
        fn.retry.wait = fn.retry.wait.__class__(0)  # type: ignore[union-attr]
        with pytest.raises(PyTrendsTimeoutError):
            client.interest_over_time("test", "US", "today 12-m", "en-US")

    @patch("app.clients.pytrends_client.TrendReq")
    def test_suggestions_success(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.suggestions.return_value = [{"title": "Test", "type": "Topic", "mid": "/m/abc"}]
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        data, payload = client.suggestions("test", "en-US")

        assert len(data) == 1
        assert data[0]["title"] == "Test"
        assert payload["keyword"] == "test"

    @patch("app.clients.pytrends_client.TrendReq")
    def test_interest_over_time_429_raises_rate_limit(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.interest_over_time.side_effect = Exception(
            "The request failed: Google returned a response with code 429"
        )
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        client._dataforseo = None  # isolate PyTrends error behavior from the fallback (env may have creds)
        fn = client._interest_over_time_pytrends
        fn.retry.wait = fn.retry.wait.__class__(0)  # type: ignore[union-attr]
        with pytest.raises(PyTrendsRateLimitError, match="Rate limited"):
            client.interest_over_time("test", "US", "today 12-m", "en-US")

    @patch("app.clients.pytrends_client.TrendsRSS")
    def test_trending_rss_success(self, mock_rss_class: MagicMock) -> None:
        mock_rss = MagicMock()
        mock_rss.get_trends.return_value = [
            {
                "title": "Bitcoin",
                "traffic": 500,
                "description": None,
                "pub_date": "2026-06-29",
                "link": "https://example.com",
                "articles": [],
                "article_count": 0,
            },
        ]
        mock_rss_class.return_value = mock_rss

        client = PyTrendsClient()
        data, payload = client.trending_rss("US", max_articles=5)

        assert len(data) == 1
        assert data[0]["title"] == "Bitcoin"
        assert payload["geo"] == "US"

    @patch("app.clients.pytrends_client.TrendReq")
    def test_categories_success(self, mock_trend_req: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.categories.return_value = {
            "name": "All categories",
            "id": 0,
            "children": [{"name": "Arts & Entertainment", "id": 3}],
        }
        mock_trend_req.return_value = mock_session

        client = PyTrendsClient()
        data, payload = client.categories("en-US")

        assert "children" in data
        assert len(data["children"]) == 1
        assert payload["language"] == "en-US"


class TestDataForSEOFallback:
    """DataForSEO is only wired in as a fallback (app/clients/dataforseo_client.py)
    — these tests isolate the fallback-triggering logic in PyTrendsClient
    itself, not the DataForSEO SDK call (see test_dataforseo_client.py for
    that). Patching the private *_pytrends method directly bypasses
    RETRY_DECORATOR entirely, which is already covered by the retry tests
    above."""

    def test_no_fallback_configured_propagates_error(self) -> None:
        client = PyTrendsClient()
        client._dataforseo = None  # fallback disabled (empty DATAFORSEO_LOGIN/PASSWORD)
        client._interest_over_time_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]

        with pytest.raises(PyTrendsRateLimitError):
            client.interest_over_time("test", "US", "today 12-m", "en-US")

    def test_falls_back_to_dataforseo_when_configured(self) -> None:
        client = PyTrendsClient()
        client._interest_over_time_pytrends = MagicMock(side_effect=PyTrendsRateLimitError("rate limited"))  # type: ignore[method-assign]
        mock_dataforseo = MagicMock()
        expected = (pd.DataFrame({"test": [10]}), {"provider": "dataforseo_fallback"})
        mock_dataforseo.interest_over_time.return_value = expected
        client._dataforseo = mock_dataforseo

        df, payload = client.interest_over_time("test", "US", "today 12-m", "en-US")

        assert payload["provider"] == "dataforseo_fallback"
        mock_dataforseo.interest_over_time.assert_called_once_with("test", "US", "today 12-m", "en-US")

    def test_dataforseo_not_triggered_on_success(self) -> None:
        client = PyTrendsClient()
        expected = (pd.DataFrame({"test": [10]}), {"provider": "pytrends"})
        client._interest_over_time_pytrends = MagicMock(return_value=expected)  # type: ignore[method-assign]
        mock_dataforseo = MagicMock()
        client._dataforseo = mock_dataforseo

        df, payload = client.interest_over_time("test", "US", "today 12-m", "en-US")

        assert payload["provider"] == "pytrends"
        mock_dataforseo.interest_over_time.assert_not_called()
