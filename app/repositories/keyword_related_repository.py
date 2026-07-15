import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.keyword_related import KeywordRelated
from app.utils.time import utc_now


class KeywordRelatedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        location: str,
        language: str,
        records: list[dict[str, Any]],
    ) -> list[KeywordRelated]:
        entities = []
        now = utc_now()
        for record in records:
            entity = KeywordRelated(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                seed_keyword=record["seed_keyword"],
                keyword=record["keyword"],
                location=location,
                language=language,
                search_volume=record.get("search_volume"),
                competition_index=record.get("competition_index"),
                cpc=record.get("cpc"),
                monthly_searches=record.get("monthly_searches"),
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[KeywordRelated]:
        result = await self._session.execute(
            select(KeywordRelated).where(KeywordRelated.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
