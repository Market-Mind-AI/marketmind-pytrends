import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.related_query import RelatedQuery
from app.utils.time import utc_now


class RelatedQueriesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        records: dict[str, list[dict[str, Any]]],
    ) -> list[RelatedQuery]:
        entities = []
        now = utc_now()
        for query_type, items in records.items():
            for item in items:
                entity = RelatedQuery(
                    id=uuid.uuid4(),
                    trend_request_id=trend_request_id,
                    keyword=keyword,
                    query=item["query"],
                    query_type=query_type,
                    value=item.get("value"),
                    created_at=now,
                )
                entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[RelatedQuery]:
        result = await self._session.execute(
            select(RelatedQuery).where(RelatedQuery.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
