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

from app.clients.dataforseo_client import DataForSEOClient
from app.core.config import settings
from app.core.exceptions import (
    PyTrendsClientError,
    PyTrendsEmptyResponseError,
    PyTrendsRateLimitError,
    PyTrendsTimeoutError,
)
from app.core.logging import logger
from app.utils.normalization import build_anchor_batches, merge_anchor_batches

# PyTrends is the highest-weighted data source (Demand dimension) — a
# transient Google Trends rate limit must not silently degrade the MOS.
# See app/core/config.py trends_rate_limit_* for the persistence rationale.
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(settings.trends_rate_limit_max_attempts),
    wait=wait_exponential_jitter(
        initial=settings.trends_rate_limit_initial_wait_seconds,
        max=settings.trends_rate_limit_max_wait_seconds,
        jitter=settings.trends_rate_limit_jitter_seconds,
    ),
    retry=retry_if_exception_type((Timeout, RequestsConnectionError, PyTrendsTimeoutError, PyTrendsRateLimitError)),
    reraise=True,
)


def _melt_region_df(df: pd.DataFrame, batch: list[tuple[str, str]]) -> pd.DataFrame:
    """Melt a multi-term interest_by_region (COUNTRY) DataFrame — one column
    per term plus an optional geoCode — into long rows
    {country, term, term_language, value}. Country is the ISO-2 geoCode when
    present, otherwise the index (country name)."""
    has_geo_code = "geoCode" in df.columns
    rows: list[dict[str, Any]] = []
    for country_name, row in df.iterrows():
        geo_code = row["geoCode"] if has_geo_code else None
        country = str(geo_code) if geo_code else str(country_name)
        for term, term_language in batch:
            value = row[term] if term in df.columns else None
            rows.append({"country": country, "term": term, "term_language": term_language, "value": value})
    long_df = pd.DataFrame(rows, columns=["country", "term", "term_language", "value"])
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    return long_df


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
        # Resilience fallback (2026-07-08) — only active once real
        # credentials are configured; empty login/password means this stays
        # None and every method behaves exactly as before it existed.
        self._dataforseo = DataForSEOClient() if settings.dataforseo_login and settings.dataforseo_password else None

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
    def _interest_over_time_pytrends(
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
                "provider": "pytrends",
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

    def interest_over_time(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        try:
            return self._interest_over_time_pytrends(keyword, country, timeframe, language)
        except (PyTrendsRateLimitError, PyTrendsTimeoutError) as e:
            if self._dataforseo is None:
                raise
            logger.warning(
                f"PyTrends exhausted retries for interest_over_time (keyword={keyword}): {e}. "
                "Falling back to DataForSEO."
            )
            return self._dataforseo.interest_over_time(keyword, country, timeframe, language)

    @RETRY_DECORATOR
    def _interest_by_region_pytrends(
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
                "provider": "pytrends",
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

    def interest_by_region(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        try:
            return self._interest_by_region_pytrends(keyword, country, timeframe, language)
        except (PyTrendsRateLimitError, PyTrendsTimeoutError) as e:
            if self._dataforseo is None:
                raise
            logger.warning(
                f"PyTrends exhausted retries for interest_by_region (keyword={keyword}): {e}. "
                "Falling back to DataForSEO."
            )
            return self._dataforseo.interest_by_region(keyword, country, timeframe, language)

    @RETRY_DECORATOR
    def _interest_by_country_pytrends(
        self, terms: list[tuple[str, str]], timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        # Compare all localized terms worldwide on ONE shared 0-100 axis. Up to
        # 5 terms are a single build_payload; more than 5 are anchor-chained (see
        # build_anchor_batches / merge_anchor_batches) so every batch is rescaled
        # onto batch 1's axis via the shared anchor term (terms[0]).
        anchor_term = terms[0][0] if terms else ""
        try:
            session = self._create_session(language)
            frames: list[pd.DataFrame] = []
            for batch in build_anchor_batches(terms):
                session.build_payload([t for t, _ in batch], cat=0, timeframe=timeframe, geo="")
                df = session.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True)
                if df.empty:
                    batch_terms = [t for t, _ in batch]
                    raise PyTrendsEmptyResponseError(f"No data returned for terms {batch_terms} worldwide")
                frames.append(_melt_region_df(df, batch))

            merged = merge_anchor_batches(frames, anchor_term)

            request_payload = {
                "terms": [{"term": t, "language": lang} for t, lang in terms],
                "timeframe": timeframe,
                "language": language,
                "provider": "pytrends",
            }

            return merged, request_payload
        except Timeout as e:
            raise PyTrendsTimeoutError(f"Timeout calling Google Trends: {e}") from e
        except (PyTrendsEmptyResponseError, PyTrendsTimeoutError, PyTrendsRateLimitError):
            raise
        except (IndexError, KeyError) as e:
            logger.warning(f"Parse error for interest_by_country: keyword={anchor_term}, retrying...")
            raise PyTrendsRateLimitError(f"Rate limited (parse error): {e}") from e
        except Exception as e:
            _handle_error("interest_by_country", anchor_term, e)
            raise

    def interest_by_country(
        self, terms: list[tuple[str, str]], timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        try:
            return self._interest_by_country_pytrends(terms, timeframe, language)
        except (PyTrendsRateLimitError, PyTrendsTimeoutError) as e:
            if self._dataforseo is None:
                raise
            anchor_term = terms[0][0] if terms else ""
            logger.warning(
                f"PyTrends exhausted retries for interest_by_country (keyword={anchor_term}): {e}. "
                "Falling back to DataForSEO."
            )
            return self._dataforseo.interest_by_country(terms, timeframe, language)

    @RETRY_DECORATOR
    def _related_queries_pytrends(
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
                "provider": "pytrends",
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

    def related_queries(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            return self._related_queries_pytrends(keyword, country, timeframe, language)
        except (PyTrendsRateLimitError, PyTrendsTimeoutError) as e:
            if self._dataforseo is None:
                raise
            logger.warning(
                f"PyTrends exhausted retries for related_queries (keyword={keyword}): {e}. "
                "Falling back to DataForSEO."
            )
            return self._dataforseo.related_queries(keyword, country, timeframe, language)

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
