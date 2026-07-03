import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trend_request import TrendRequest
from app.utils.time import utc_now


class TrendRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        ingestion_run_id: uuid.UUID,
        keyword: str,
        country: str,
        endpoint: str,
        language: str | None = None,
        timeframe: str | None = None,
    ) -> TrendRequest:
        tr = TrendRequest(
            id=uuid.uuid4(),
            ingestion_run_id=ingestion_run_id,
            keyword=keyword,
            country=country,
            language=language,
            timeframe=timeframe,
            endpoint=endpoint,
            created_at=utc_now(),
        )
        self._session.add(tr)
        await self._session.flush()
        return tr

    async def get_by_id(self, request_id: uuid.UUID) -> TrendRequest | None:
        result = await self._session.execute(select(TrendRequest).where(TrendRequest.id == request_id))
        return result.scalar_one_or_none()
