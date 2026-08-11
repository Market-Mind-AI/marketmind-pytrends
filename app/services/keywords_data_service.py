import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.dataforseo_client import DataForSEOClient
from app.core.logging import logger
from app.domain.enums import IngestionStatus, KeywordEndpoint
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.keyword_related_repository import KeywordRelatedRepository
from app.repositories.keyword_search_volume_repository import KeywordSearchVolumeRepository
from app.repositories.raw_api_response_repository import RawApiResponseRepository
from app.repositories.trend_request_repository import TrendRequestRepository
from app.schemas.requests import KeywordsForKeywordsRequest, SearchVolumeRequest
from app.schemas.responses import (
    KeywordsForKeywordsData,
    KeywordsForKeywordsRequestInfo,
    KeywordsForKeywordsResponse,
    Metadata,
    RelatedKeywordItem,
    SearchVolumeData,
    SearchVolumeItem,
    SearchVolumeRequestInfo,
    SearchVolumeResponse,
)
from app.utils.time import elapsed_ms, utc_now

_SOURCE = "dataforseo_google_ads"


class KeywordsDataService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = DataForSEOClient()
        self._ingestion_repo = IngestionRunRepository(session)
        self._trend_request_repo = TrendRequestRepository(session)
        self._raw_response_repo = RawApiResponseRepository(session)
        self._sv_repo = KeywordSearchVolumeRepository(session)
        self._kr_repo = KeywordRelatedRepository(session)

    async def collect_search_volume(self, request: SearchVolumeRequest) -> SearchVolumeResponse:
        endpoint = KeywordEndpoint.SEARCH_VOLUME
        start = utc_now()
        keyword_label = ", ".join(request.keywords)
        run = await self._ingestion_repo.create(source=_SOURCE, request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=keyword_label,
            country=request.location,
            endpoint=endpoint,
            language=request.language,
        )
        try:
            # asyncio.to_thread, not a direct call. DataForSEOClient's methods are
            # plain `def` — the SDK underneath is synchronous — so invoking one
            # from a coroutine blocks the event loop for the entire round trip to
            # Google Ads. Nothing else in this process gets served while it runs,
            # including GET /health.
            #
            # That was not a theoretical cost. In the cluster the liveness probe
            # tolerates 30s x 3 = 90s of silence, and a keywords_for_keywords call
            # measured 120s, so the kubelet killed the container mid-collection
            # every single time: 'Liveness probe failed: context deadline
            # exceeded' -> 'Container app failed liveness probe, will be
            # restarted' -> exit 137. The task failed, every later task in the
            # same analysis failed with ConnectError against a pod that no longer
            # existed, and the next analysis retried the same doomed work. Any
            # collection slower than 90s could never succeed.
            #
            # Handing the blocking call to a worker thread keeps the loop free to
            # answer probes while Google takes its time. It is also what makes
            # concurrent collection possible at all — a blocked loop serialises
            # everything regardless of how the caller fans out.
            records, req_payload = await asyncio.to_thread(
                self._client.search_volume,
                keywords=request.keywords,
                country=request.location,
                language=request.language,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=records,
            )
            await self._sv_repo.bulk_create(
                trend_request_id=trend_req.id,
                location=request.location,
                language=request.language,
                records=records,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, keyword_label, request.location, run.id, trend_req.id, exec_time, len(records))
            return SearchVolumeResponse(
                request=SearchVolumeRequestInfo(
                    location=request.location, language=request.language, keywords=request.keywords
                ),
                metadata=self._meta(endpoint, exec_time, len(records), run.id, trend_req.id),
                data=SearchVolumeData(keywords=[SearchVolumeItem(**r) for r in records]),
            )
        except Exception as e:
            await self._fail(run, endpoint, keyword_label, request.location, start, e)
            raise

    async def collect_keywords_for_keywords(
        self, request: KeywordsForKeywordsRequest
    ) -> KeywordsForKeywordsResponse:
        endpoint = KeywordEndpoint.KEYWORDS_FOR_KEYWORDS
        start = utc_now()
        seed_label = ", ".join(request.seed_keywords)
        run = await self._ingestion_repo.create(source=_SOURCE, request_payload=request.model_dump())
        trend_req = await self._trend_request_repo.create(
            ingestion_run_id=run.id,
            keyword=seed_label,
            country=request.location,
            endpoint=endpoint,
            language=request.language,
        )
        try:
            # Same blocking-call problem as search_volume above, and this is the
            # method that actually triggered the kill loop — see the note there.
            records, req_payload = await asyncio.to_thread(
                self._client.keywords_for_keywords,
                seed_keywords=request.seed_keywords,
                country=request.location,
                language=request.language,
                limit=request.limit,
            )
            await self._raw_response_repo.create(
                trend_request_id=trend_req.id,
                endpoint=endpoint,
                request_payload=req_payload,
                response_payload=records,
            )
            await self._kr_repo.bulk_create(
                trend_request_id=trend_req.id,
                location=request.location,
                language=request.language,
                records=records,
            )
            exec_time = elapsed_ms(start)
            await self._ingestion_repo.mark_success(run, exec_time)
            await self._session.commit()
            self._log_success(endpoint, seed_label, request.location, run.id, trend_req.id, exec_time, len(records))
            return KeywordsForKeywordsResponse(
                request=KeywordsForKeywordsRequestInfo(
                    location=request.location,
                    language=request.language,
                    seed_keywords=request.seed_keywords,
                    limit=request.limit,
                ),
                metadata=self._meta(endpoint, exec_time, len(records), run.id, trend_req.id),
                data=KeywordsForKeywordsData(keywords=[RelatedKeywordItem(**r) for r in records]),
            )
        except Exception as e:
            await self._fail(run, endpoint, seed_label, request.location, start, e)
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
        if tr.endpoint == KeywordEndpoint.SEARCH_VOLUME:
            sv_records = await self._sv_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {
                    "keyword": r.keyword,
                    "search_volume": float(r.search_volume) if r.search_volume is not None else None,
                    "competition": r.competition,
                    "competition_index": r.competition_index,
                    "cpc": float(r.cpc) if r.cpc is not None else None,
                    "monthly_searches": r.monthly_searches,
                }
                for r in sv_records
            ]
        elif tr.endpoint == KeywordEndpoint.KEYWORDS_FOR_KEYWORDS:
            kr_records = await self._kr_repo.get_by_trend_request_id(trend_request_id)
            result["data"] = [
                {
                    "seed_keyword": r.seed_keyword,
                    "keyword": r.keyword,
                    "search_volume": float(r.search_volume) if r.search_volume is not None else None,
                    "competition_index": r.competition_index,
                    "cpc": float(r.cpc) if r.cpc is not None else None,
                    "monthly_searches": r.monthly_searches,
                }
                for r in kr_records
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

    async def _fail(self, run: Any, endpoint: str, keyword: str, location: str, start: Any, error: Exception) -> None:
        exec_time = elapsed_ms(start)
        await self._ingestion_repo.mark_failed(run, str(error), exec_time)
        await self._session.commit()
        self._log_failure(endpoint, keyword, location, run.id, exec_time, str(error))

    def _log_success(
        self,
        endpoint: str,
        keyword: str,
        location: str,
        run_id: Any,
        trend_request_id: Any,
        exec_time: int,
        records: int,
    ) -> None:
        logger.info(
            f"endpoint={endpoint} | keyword={keyword} | location={location} | "
            f"ingestion_run_id={run_id} | trend_request_id={trend_request_id} | "
            f"execution_time_ms={exec_time} | records={records} | status=success"
        )

    def _log_failure(
        self,
        endpoint: str,
        keyword: str,
        location: str,
        run_id: Any,
        exec_time: int,
        error: str,
    ) -> None:
        logger.error(
            f"endpoint={endpoint} | keyword={keyword} | location={location} | "
            f"ingestion_run_id={run_id} | execution_time_ms={exec_time} | "
            f"status=failed | error={error}"
        )
