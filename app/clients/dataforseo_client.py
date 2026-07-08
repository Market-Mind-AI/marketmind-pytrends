"""DataForSEO fallback for PyTrendsClient (app/clients/pytrends_client.py).
Only called after PyTrends' own retries (RETRY_DECORATOR there) are
exhausted — this is a resilience net for the highest-weighted data source
(Demand dimension), not a primary path. Uses the official `dataforseo-client`
SDK (sync, like `pytrends_modern` — no asyncio.to_thread, matching this
project's existing style of calling sync clients directly from async
service methods).

A single Explore Live call with <=1 keyword returns interest-over-time,
interest-by-region, and related-queries data together (confirmed against
the real API docs 2026-07-08, not assumed) — one DataForSEO task covers
everything marketmind-core's analysis pipeline actually consumes
(_PYTRENDS_INDICATOR_CODES in analysis_service.py), instead of 3 separate
calls. related_topics is fetched by neither PyTrends nor this fallback
today — nothing in the automated pipeline consumes it.

Sandbox vs Live is a plain host swap (settings.dataforseo_use_sandbox) —
same auth, same request/response shape, sandbox never bills and returns
mock data (see scripts/verify_dataforseo_locations.py docstring for the
same sandbox/live note applied to the locations endpoint).
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from dataforseo_client import api_client as dfs_api_provider
from dataforseo_client import configuration as dfs_config
from dataforseo_client.api.keywords_data_api import KeywordsDataApi
from dataforseo_client.models.google_trends_google_trends_graph_element_item import (
    GoogleTrendsGoogleTrendsGraphElementItem,
)
from dataforseo_client.models.google_trends_google_trends_map_element_item import (
    GoogleTrendsGoogleTrendsMapElementItem,
)
from dataforseo_client.models.google_trends_google_trends_queries_list_element_item import (
    GoogleTrendsGoogleTrendsQueriesListElementItem,
)
from dataforseo_client.models.keywords_data_google_trends_explore_live_request_info import (
    KeywordsDataGoogleTrendsExploreLiveRequestInfo,
)
from dataforseo_client.rest import ApiException

from app.clients.dataforseo_locations import ISO2_TO_LOCATION_NAME, UNSUPPORTED_ISO2
from app.core.config import settings
from app.core.exceptions import DataForSEOClientError
from app.core.logging import logger

_SANDBOX_HOST = "https://sandbox.dataforseo.com"
# DataForSEO status codes are 20000-series for success, 40000+ for errors —
# same convention documented across their whole API, not fallback-specific.
_TASK_ERROR_THRESHOLD = 40000

# The only shape this project ever actually sends (see
# app/schemas/requests.py TrendRequest.timeframe default, "today 12-m") —
# parsed deterministically into an explicit date range DataForSEO needs.
# Anything else falls back to the last 12 months, always logged so it's
# never a silent surprise.
_TIMEFRAME_PATTERN = re.compile(r"^today (\d+)-([my])$")


def _timeframe_to_date_range(timeframe: str) -> tuple[str, str]:
    today = datetime.now(UTC).date()
    match = _TIMEFRAME_PATTERN.match(timeframe.strip())
    if match is None:
        logger.warning(f"Unrecognized timeframe '{timeframe}' for DataForSEO fallback — defaulting to last 12 months")
        return (today - timedelta(days=365)).isoformat(), today.isoformat()
    amount, unit = int(match.group(1)), match.group(2)
    days = amount * 365 if unit == "y" else amount * 30
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


def _request_payload(keyword: str, country: str, timeframe: str, language: str) -> dict[str, Any]:
    return {
        "keyword": keyword,
        "country": country,
        "timeframe": timeframe,
        "language": language,
        "provider": "dataforseo_fallback",
    }


class DataForSEOClient:
    def _location_name(self, country: str) -> str:
        if country in UNSUPPORTED_ISO2:
            raise DataForSEOClientError(
                f"DataForSEO does not support country '{country}' (sanctioned — confirmed in their own docs)"
            )
        location_name = ISO2_TO_LOCATION_NAME.get(country)
        if location_name is None:
            raise DataForSEOClientError(
                f"No DataForSEO location_name mapping for country '{country}' — add it to "
                "app/clients/dataforseo_locations.py and confirm with scripts/verify_dataforseo_locations.py"
            )
        return location_name

    def _explore(self, keyword: str, country: str, timeframe: str) -> list[Any]:
        location_name = self._location_name(country)
        date_from, date_to = _timeframe_to_date_range(timeframe)
        host = _SANDBOX_HOST if settings.dataforseo_use_sandbox else None
        configuration = dfs_config.Configuration(
            username=settings.dataforseo_login, password=settings.dataforseo_password, host=host
        )
        try:
            with dfs_api_provider.ApiClient(configuration) as api_client:
                api = KeywordsDataApi(api_client)
                response = api.google_trends_explore_live(
                    [
                        KeywordsDataGoogleTrendsExploreLiveRequestInfo(
                            keywords=[keyword],
                            location_name=location_name,
                            date_from=date_from,
                            date_to=date_to,
                            item_types=["google_trends_graph", "google_trends_map", "google_trends_queries_list"],
                        )
                    ]
                )
        except ApiException as exc:
            raise DataForSEOClientError(f"DataForSEO API error for keyword '{keyword}': {exc}") from exc

        tasks = response.tasks or []
        if not tasks:
            raise DataForSEOClientError(f"DataForSEO returned no tasks for keyword '{keyword}' in '{country}'")
        task = tasks[0]
        if task is None:
            raise DataForSEOClientError(f"DataForSEO returned an empty task for keyword '{keyword}' in '{country}'")
        if task.status_code is not None and task.status_code >= _TASK_ERROR_THRESHOLD:
            raise DataForSEOClientError(f"DataForSEO task failed ({task.status_code}): {task.status_message}")
        if not task.result:
            raise DataForSEOClientError(f"DataForSEO returned no result for keyword '{keyword}' in '{country}'")
        return list(task.result[0].items or []) if task.result[0] is not None else []

    def interest_over_time(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        items = self._explore(keyword, country, timeframe)
        graph = next((i for i in items if isinstance(i, GoogleTrendsGoogleTrendsGraphElementItem)), None)
        if graph is None or not graph.data:
            raise DataForSEOClientError(f"DataForSEO returned no interest-over-time data for keyword '{keyword}'")

        rows: list[dict[str, Any]] = []
        for point in graph.data:
            if point is None or point.date_from is None:
                continue
            value = point.values[0] if point.values else 0
            rows.append({"date": point.date_from, "value": value, "isPartial": bool(point.missing_data)})
        df = pd.DataFrame(rows).set_index("date").rename(columns={"value": keyword})
        df.index = pd.to_datetime(df.index)
        return df, _request_payload(keyword, country, timeframe, language)

    def interest_by_region(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        items = self._explore(keyword, country, timeframe)
        map_item = next((i for i in items if isinstance(i, GoogleTrendsGoogleTrendsMapElementItem)), None)
        if map_item is None or not map_item.data:
            raise DataForSEOClientError(f"DataForSEO returned no interest-by-region data for keyword '{keyword}'")

        rows: list[dict[str, Any]] = []
        for point in map_item.data:
            if point is None or point.geo_name is None:
                continue
            value = point.values[0] if point.values else 0
            rows.append({"region": point.geo_name, "value": value})
        df = pd.DataFrame(rows).set_index("region").rename(columns={"value": keyword})
        return df, _request_payload(keyword, country, timeframe, language)

    def related_queries(
        self, keyword: str, country: str, timeframe: str, language: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        items = self._explore(keyword, country, timeframe)
        queries_item = next((i for i in items if isinstance(i, GoogleTrendsGoogleTrendsQueriesListElementItem)), None)

        top_df = pd.DataFrame(columns=["query", "value"])
        rising_df = pd.DataFrame(columns=["query", "value"])
        if queries_item is not None and queries_item.data is not None:
            if queries_item.data.top:
                top_df = pd.DataFrame(
                    [{"query": e.get("query", ""), "value": e.get("value")} for e in queries_item.data.top if e]
                )
            if queries_item.data.rising:
                rising_df = pd.DataFrame(
                    [{"query": e.get("query", ""), "value": e.get("value")} for e in queries_item.data.rising if e]
                )
        data = {keyword: {"top": top_df, "rising": rising_df}}
        return data, _request_payload(keyword, country, timeframe, language)
