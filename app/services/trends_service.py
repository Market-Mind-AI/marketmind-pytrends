from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.pytrends_client import PyTrendsClient
from app.core.logging import logger
from app.domain.enums import IngestionStatus, TrendEndpoint
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.interest_by_country_repository import InterestByCountryRepository
from app.repositories.interest_by_region_repository import InterestByRegionRepository
from app.repositories.interest_over_time_repository import InterestOverTimeRepository
from app.repositories.raw_api_response_repository import RawApiResponseRepository
from app.repositories.related_queries_repository import RelatedQueriesRepository
from app.repositories.related_topics_repository import RelatedTopicsRepository
from app.repositories.suggestions_repository import SuggestionsRepository
from app.repositories.trend_request_repository import TrendRequestRepository
from app.repositories.trending_rss_repository import TrendingRssRepository
from app.schemas.requests import SuggestionRequest, TrendingRssRequest, TrendRequest, WorldwideTrendRequest
from app.schemas.responses import (
    CategoriesResponse,
    CountryItem,
    InterestByCountryData,
    InterestByCountryResponse,
    InterestByRegionData,
    InterestByRegionResponse,
    InterestOverTimeData,
    InterestOverTimeItem,
    InterestOverTimeResponse,
    Metadata,
    QueryItem,
    RegionItem,
    RelatedQueriesData,
    RelatedQueriesResponse,
    RelatedTopicsData,
    RelatedTopicsResponse,
    RequestInfo,
    SuggestionItem,
    SuggestionsData,
    SuggestionsResponse,
    TopicItem,
    TrendingRssData,
    TrendingRssItem,
    TrendingRssResponse,
)
from app.utils.normalization import (
    dataframe_to_json_serializable,
    dict_with_dataframes_to_serializable,
    normalize_interest_by_country,
    normalize_interest_by_region,
    normalize_interest_over_time,
    normalize_related_queries,
    normalize_related_topics,
    normalize_suggestions,
)
from app.utils.time import elapsed_ms, utc_now


class TrendsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = PyTrendsClient()
        self._ingestion_repo = IngestionRunRepository(session)
        self._trend_request_repo = TrendRequestRepository(session)
        self._raw_response_repo = RawApiResponseRepository(session)
        self._iot_repo = InterestOverTimeRepository(session)
        self._ibr_repo = InterestByRegionRepository(session)
        self._ibc_repo = InterestByCountryRepository(session)
        self._rq_repo = RelatedQueriesRepository(session)
        self._rt_repo = RelatedTopicsRepository(session)
        self._suggestions_repo = SuggestionsRepository(session)
        self._trending_rss_repo = TrendingRssRepository(session)

    async def collect_interest_over_time(self, request: TrendRequest) -> InterestOverTimeResponse:
        endpoint = TrendEndpoint.INTEREST_OVER_TIME
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country=request.country,
            endpoint=endpoint,
            language=request.language,
            timeframe=request.timeframe,
        )
        try:
            df, req_payload = self._client.interest_over_time(
                keyword=request.keyword,
                country=request.country,
                timeframe=request.timeframe,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=dataframe_to_json_serializable(df),
            )
            normalized = normalize_interest_over_time(df, request.keyword)
            await self._iot_repo.bulk_create(
                trend_request_id=trend_req.id,
                keyword=request.keyword,
                country=request.country,
                records=normalized,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(
                endpoint,
                request.keyword,
                request.country,
                run.id,
                trend_req.id,
                exec_time,
                len(normalized),
            )
            return InterestOverTimeResponse(
                request=self._req_info(request),
                metadata=self._meta(endpoint, exec_time, len(normalized), run.id, trend_req.id),
                data=InterestOverTimeData(interest_over_time=[InterestOverTimeItem(**r) for r in normalized]),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, request.country, start, e)
            raise

    async def collect_interest_by_region(self, request: TrendRequest) -> InterestByRegionResponse:
        endpoint = TrendEndpoint.INTEREST_BY_REGION
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country=request.country,
            endpoint=endpoint,
            language=request.language,
            timeframe=request.timeframe,
        )
        try:
            df, req_payload = self._client.interest_by_region(
                keyword=request.keyword,
                country=request.country,
                timeframe=request.timeframe,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=dataframe_to_json_serializable(df),
            )
            normalized = normalize_interest_by_region(df, request.keyword)
            await self._ibr_repo.bulk_create(
                trend_request_id=trend_req.id,
                keyword=request.keyword,
                country=request.country,
                records=normalized,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(
                endpoint,
                request.keyword,
                request.country,
                run.id,
                trend_req.id,
                exec_time,
                len(normalized),
            )
            return InterestByRegionResponse(
                request=self._req_info(request),
                metadata=self._meta(endpoint, exec_time, len(normalized), run.id, trend_req.id),
                data=InterestByRegionData(regions=[RegionItem(**r) for r in normalized]),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, request.country, start, e)
            raise

    async def collect_interest_by_country(self, request: WorldwideTrendRequest) -> InterestByCountryResponse:
        endpoint = TrendEndpoint.INTEREST_BY_COUNTRY
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country="WORLD",
            endpoint=endpoint,
            language=request.language,
            timeframe=request.timeframe,
        )
        try:
            df, req_payload = self._client.interest_by_country(
                keyword=request.keyword,
                timeframe=request.timeframe,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=dataframe_to_json_serializable(df),
            )
            normalized = normalize_interest_by_country(df, request.keyword)
            await self._ibc_repo.bulk_create(
                trend_request_id=trend_req.id,
                keyword=request.keyword,
                records=normalized,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(
                endpoint,
                request.keyword,
                "WORLD",
                run.id,
                trend_req.id,
                exec_time,
                len(normalized),
            )
            return InterestByCountryResponse(
                request=RequestInfo(
                    keyword=request.keyword,
                    country="WORLD",
                    timeframe=request.timeframe,
                    language=request.language,
                ),
                metadata=self._meta(endpoint, exec_time, len(normalized), run.id, trend_req.id),
                data=InterestByCountryData(countries=[CountryItem(**r) for r in normalized]),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, "WORLD", start, e)
            raise

    async def collect_related_queries(self, request: TrendRequest) -> RelatedQueriesResponse:
        endpoint = TrendEndpoint.RELATED_QUERIES
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country=request.country,
            endpoint=endpoint,
            language=request.language,
            timeframe=request.timeframe,
        )
        try:
            data, req_payload = self._client.related_queries(
                keyword=request.keyword,
                country=request.country,
                timeframe=request.timeframe,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=dict_with_dataframes_to_serializable(data),
            )
            normalized = normalize_related_queries(data, request.keyword)
            await self._rq_repo.bulk_create(trend_request_id=trend_req.id, keyword=request.keyword, records=normalized)
            total = len(normalized["top"]) + len(normalized["rising"])
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, request.keyword, request.country, run.id, trend_req.id, exec_time, total)
            return RelatedQueriesResponse(
                request=self._req_info(request),
                metadata=self._meta(endpoint, exec_time, total, run.id, trend_req.id),
                data=RelatedQueriesData(
                    top=[QueryItem(**r) for r in normalized["top"]],
                    rising=[QueryItem(**r) for r in normalized["rising"]],
                ),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, request.country, start, e)
            raise

    async def collect_related_topics(self, request: TrendRequest) -> RelatedTopicsResponse:
        endpoint = TrendEndpoint.RELATED_TOPICS
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country=request.country,
            endpoint=endpoint,
            language=request.language,
            timeframe=request.timeframe,
        )
        try:
            data, req_payload = self._client.related_topics(
                keyword=request.keyword,
                country=request.country,
                timeframe=request.timeframe,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=dict_with_dataframes_to_serializable(data),
            )
            normalized = normalize_related_topics(data, request.keyword)
            await self._rt_repo.bulk_create(trend_request_id=trend_req.id, keyword=request.keyword, records=normalized)
            total = len(normalized["top"]) + len(normalized["rising"])
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, request.keyword, request.country, run.id, trend_req.id, exec_time, total)
            return RelatedTopicsResponse(
                request=self._req_info(request),
                metadata=self._meta(endpoint, exec_time, total, run.id, trend_req.id),
                data=RelatedTopicsData(
                    top=[TopicItem(**r) for r in normalized["top"]],
                    rising=[TopicItem(**r) for r in normalized["rising"]],
                ),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, request.country, start, e)
            raise

    async def collect_suggestions(self, request: SuggestionRequest) -> SuggestionsResponse:
        endpoint = TrendEndpoint.SUGGESTIONS
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=request.keyword,
            country="",
            endpoint=endpoint,
            language=request.language,
        )
        try:
            data, req_payload = self._client.suggestions(keyword=request.keyword, language=request.language)
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=data,
            )
            normalized = normalize_suggestions(data)
            await self._suggestions_repo.bulk_create(
                trend_request_id=trend_req.id,
                keyword=request.keyword,
                records=normalized,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, request.keyword, "", run.id, trend_req.id, exec_time, len(normalized))
            return SuggestionsResponse(
                request=RequestInfo(keyword=request.keyword, country="", language=request.language),
                metadata=self._meta(endpoint, exec_time, len(normalized), run.id, trend_req.id),
                data=SuggestionsData(suggestions=[SuggestionItem(**r) for r in normalized]),
            )
        except Exception as e:
            await self._fail(run, endpoint, request.keyword, "", start, e)
            raise

    async def collect_trending_rss(self, request: TrendingRssRequest) -> TrendingRssResponse:
        endpoint = TrendEndpoint.TRENDING_RSS
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends_rss", request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword="__trending__",
            country=request.geo,
            endpoint=endpoint,
            language=request.language,
        )
        try:
            data, req_payload = self._client.trending_rss(geo=request.geo, max_articles=request.max_articles)
            raw_serializable = [{k: str(v) if hasattr(v, "isoformat") else v for k, v in item.items()} for item in data]
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=raw_serializable,
            )
            normalized = [
                {
                    "title": t.get("title", ""),
                    "traffic": t.get("traffic"),
                    "description": t.get("description"),
                    "pub_date": str(t["pub_date"]) if t.get("pub_date") else None,
                    "link": t.get("link"),
                    "articles": t.get("articles", []),
                    "article_count": t.get("article_count", 0),
                }
                for t in data
            ]
            await self._trending_rss_repo.bulk_create(
                trend_request_id=trend_req.id,
                geo=request.geo,
                records=normalized,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, "__trending__", request.geo, run.id, trend_req.id, exec_time, len(normalized))
            return TrendingRssResponse(
                request=RequestInfo(keyword="__trending__", country=request.geo, language=request.language),
                metadata=self._meta(endpoint, exec_time, len(normalized), run.id, trend_req.id),
                data=TrendingRssData(trends=[TrendingRssItem(**r) for r in normalized]),
            )
        except Exception as e:
            await self._fail(run, endpoint, "__trending__", request.geo, start, e)
            raise

    async def collect_categories(self, language: str) -> CategoriesResponse:
        endpoint = TrendEndpoint.CATEGORIES
        start = utc_now()
        run = await self._ingestion_repo.create(source="google_trends", request_payload={"language": language})
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword="__categories__",
            country="",
            endpoint=endpoint,
            language=language,
        )
        try:
            data, req_payload = self._client.categories(language=language)
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=data,
            )
            children = data.get("children", []) if isinstance(data, dict) else []
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, "__categories__", "", run.id, trend_req.id, exec_time, len(children))
            return CategoriesResponse(
                request=RequestInfo(keyword="__categories__", country="", language=language),
                metadata=self._meta(endpoint, exec_time, len(children), run.id, trend_req.id),
                data=data if isinstance(data, dict) else {"categories": data},
            )
        except Exception as e:
            await self._fail(run, endpoint, "__categories__", "", start, e)
            raise

    async def get_trend_request(self, trend_request_id: Any) -> dict[str, Any] | None:
        tr = await self._trend_request_repo.get_by_id(trend_request_id)
        if not tr:
            return None
        result: dict[str, Any] = {
            "id": tr.id,
            "ingestion_run_id": tr.ingestion_run_id,
            "keyword": tr.keyword,
            "country": tr.country,
            "language": tr.language,
            "timeframe": tr.timeframe,
            "endpoint": tr.endpoint,
            "created_at": tr.created_at,
            "data": [],
        }
        if tr.endpoint == TrendEndpoint.INTEREST_OVER_TIME:
            records = await self._iot_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {"date": str(r.date), "value": float(r.interest_value), "is_partial": r.is_partial} for r in records
            ]
        elif tr.endpoint == TrendEndpoint.INTEREST_BY_REGION:
            records = await self._ibr_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [{"region": r.region, "value": float(r.interest_value)} for r in records]
        elif tr.endpoint == TrendEndpoint.INTEREST_BY_COUNTRY:
            ibc_records = await self._ibc_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [{"region": r.country, "value": float(r.interest_value)} for r in ibc_records]
        elif tr.endpoint == TrendEndpoint.RELATED_QUERIES:
            records = await self._rq_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {"query": r.query, "query_type": r.query_type, "value": float(r.value) if r.value else None}
                for r in records
            ]
        elif tr.endpoint == TrendEndpoint.RELATED_TOPICS:
            records = await self._rt_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {
                    "topic": r.topic,
                    "topic_type": r.topic_type,
                    "topic_mid": r.topic_mid,
                    "value": float(r.value) if r.value else None,
                }
                for r in records
            ]
        elif tr.endpoint == TrendEndpoint.SUGGESTIONS:
            records = await self._suggestions_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [{"title": r.title, "type": r.type, "mid": r.mid} for r in records]
        elif tr.endpoint == TrendEndpoint.TRENDING_RSS:
            records = await self._trending_rss_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {
                    "title": r.title,
                    "traffic": r.traffic,
                    "pub_date": r.pub_date,
                    "articles": r.articles,
                    "article_count": r.article_count,
                }
                for r in records
            ]
        return result

    async def get_ingestion_run(self, run_id: Any) -> dict[str, Any] | None:
        run = await self._ingestion_repo.get_by_id(run_id)
        if not run:
            return None
        return {
            "id": run.id,
            "source": run.source,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "execution_time_ms": run.execution_time_ms,
            "request_payload": run.request_payload,
            "error_message": run.error_message,
            "created_at": run.created_at,
        }

    def _req_info(self, request: TrendRequest) -> RequestInfo:
        return RequestInfo(
            keyword=request.keyword,
            country=request.country,
            timeframe=request.timeframe,
            language=request.language,
        )

    def _meta(self, endpoint: str, exec_time: int, records: int, run_id: Any, trend_req_id: Any) -> Metadata:
        return Metadata(
            endpoint=endpoint,
            execution_time_ms=exec_time,
            records=records,
            ingestion_run_id=run_id,
            trend_request_id=trend_req_id,
            status=IngestionStatus.SUCCESS,
            collected_at=utc_now(),
        )

    async def _fail(self, run: Any, endpoint: str, keyword: str, country: str, start: Any, error: Exception) -> None:
        exec_time = elapsed_ms(start)
        await self._ingestion_repo.mark_failed(run, str(error), exec_time)
        await self._session.commit()
        self._log_failure(endpoint, keyword, country, run.id, exec_time, str(error))

    def _log_success(
        self,
        endpoint: str,
        keyword: str,
        country: str,
        run_id: Any,
        trend_request_id: Any,
        exec_time: int,
        records: int,
    ) -> None:
        logger.info(
            f"endpoint={endpoint} | keyword={keyword} | country={country} | "
            f"ingestion_run_id={run_id} | trend_request_id={trend_request_id} | "
            f"execution_time_ms={exec_time} | records={records} | status=success"
        )

    def _log_failure(
        self,
        endpoint: str,
        keyword: str,
        country: str,
        run_id: Any,
        exec_time: int,
        error: str,
    ) -> None:
        logger.error(
            f"endpoint={endpoint} | keyword={keyword} | country={country} | "
            f"ingestion_run_id={run_id} | execution_time_ms={exec_time} | "
            f"status=failed | error={error}"
        )
