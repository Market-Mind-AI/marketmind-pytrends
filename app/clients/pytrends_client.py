from typing import Any

import pandas as pd
from pytrends_modern import TrendReq, TrendsRSS
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings
from app.core.exceptions import (
    PyTrendsClientError,
    PyTrendsEmptyResponseError,
    PyTrendsRateLimitError,
    PyTrendsTimeoutError,
)
from app.core.logging import logger

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=10, max=120, jitter=5),
    retry=retry_if_exception_type((Timeout, RequestsConnectionError, PyTrendsTimeoutError, PyTrendsRateLimitError)),
    reraise=True,
)


def _handle_error(method_name: str, keyword: str, e: Exception) -> None:
    error_msg = str(e)
    if "429" in error_msg or "TooManyRequests" in type(e).__name__ or "too many" in error_msg.lower():
        logger.warning(f"Rate limited for {method_name}: keyword={keyword}, retrying...")
        raise PyTrendsRateLimitError(f"Rate limited by Google Trends: {e}") from e
    logger.error(f"Error in {method_name}: {e}")
    raise PyTrendsClientError(f"Error calling Google Trends: {e}") from e


class PyTrendsClient:
    def __init__(self) -> None:
        self._timeout = settings.default_timeout
        self._retries = settings.default_retries
        self._backoff = settings.default_backoff
        self._tz = settings.default_tz

    def _create_session(self, language: str) -> TrendReq:
        return TrendReq(
            hl=language,
            tz=self._tz,
            timeout=(self._timeout, self._timeout),
            retries=self._retries,
            backoff_factor=self._backoff,
            rotate_user_agent=True,
        )

    @RETRY_DECORATOR
    def interest_over_time(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        try:
            session = self._create_session(language)
            session.build_payload([keyword], cat=0, timeframe=timeframe, geo=country)
            df = session.interest_over_time()

            request_payload = {
                "keyword": keyword,
                "country": country,
                "timeframe": timeframe,
                "language": language,
            }

            if df.empty:
                raise PyTrendsEmptyResponseError(f"No data returned for keyword '{keyword}' in country '{country}'")

            return df, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsEmptyResponseError, PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except (IndexError, KeyError) as e:
            logger.warning(f"Parse error for interest_over_time: keyword={keyword}, retrying...")
            raise PyTrendsRateLimitError(f"Rate limited (parse error): {e}") from e
        except Exception as e:
            _handle_error("interest_over_time", keyword, e)
            raise  # unreachable, satisfies type checker

    @RETRY_DECORATOR
    def interest_by_region(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        try:
            session = self._create_session(language)
            session.build_payload([keyword], cat=0, timeframe=timeframe, geo=country)
            df = session.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=False)

            request_payload = {
                "keyword": keyword,
                "country": country,
                "timeframe": timeframe,
                "language": language,
            }

            if df.empty:
                raise PyTrendsEmptyResponseError(f"No data returned for keyword '{keyword}' in country '{country}'")

            return df, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsEmptyResponseError, PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except (IndexError, KeyError) as e:
            logger.warning(f"Parse error for interest_by_region: keyword={keyword}, retrying...")
            raise PyTrendsRateLimitError(f"Rate limited (parse error): {e}") from e
        except Exception as e:
            _handle_error("interest_by_region", keyword, e)
            raise

    @RETRY_DECORATOR
    def related_queries(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            session = self._create_session(language)
            session.build_payload([keyword], cat=0, timeframe=timeframe, geo=country)
            data = session.related_queries()

            request_payload = {
                "keyword": keyword,
                "country": country,
                "timeframe": timeframe,
                "language": language,
            }

            return data, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except (IndexError, KeyError) as e:
            logger.warning(f"Parse error for related_queries: keyword={keyword}, retrying...")
            raise PyTrendsRateLimitError(f"Rate limited (parse error): {e}") from e
        except Exception as e:
            _handle_error("related_queries", keyword, e)
            raise

    @RETRY_DECORATOR
    def related_topics(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            session = self._create_session(language)
            session.build_payload([keyword], cat=0, timeframe=timeframe, geo=country)
            data = session.related_topics()

            request_payload = {
                "keyword": keyword,
                "country": country,
                "timeframe": timeframe,
                "language": language,
            }

            return data, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except Exception as e:
            _handle_error("related_topics", keyword, e)
            raise

    @RETRY_DECORATOR
    def suggestions(self, keyword: str, language: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        try:
            session = self._create_session(language)
            data = session.suggestions(keyword)

            request_payload = {
                "keyword": keyword,
                "language": language,
            }

            return data, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except Exception as e:
            _handle_error("suggestions", keyword, e)
            raise

    @RETRY_DECORATOR
    def categories(self, language: str) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            session = self._create_session(language)
            data = session.categories()

            request_payload = {"language": language}

            return data, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except Exception as e:
            _handle_error("categories", "", e)
            raise

    def trending_rss(self, geo: str, max_articles: int = 5) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        try:
            rss = TrendsRSS(timeout=self._timeout)
            trends = rss.get_trends(
                geo=geo,
                output_format="dict",
                include_images=False,
                include_articles=True,
                max_articles_per_trend=max_articles,
            )

            request_payload = {
                "geo": geo,
                "max_articles": max_articles,
            }

            return trends, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends RSS: {e}") from e
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "too many" in error_msg.lower():
                raise PyTrendsRateLimitError(f"Rate limited by Google Trends RSS: {e}") from e
            logger.error(f"Error in trending_rss: {e}")
            raise PyTrendsClientError(f"Error calling Google Trends RSS: {e}") from e
