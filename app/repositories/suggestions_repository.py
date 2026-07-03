import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.suggestion import Suggestion
from app.utils.time import utc_now


class SuggestionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        records: list[dict[str, Any]],
    ) -> list[Suggestion]:
        entities = []
        now = utc_now()
        for item in records:
            entity = Suggestion(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=keyword,
                title=item["title"],
                type=item.get("type"),
                mid=item.get("mid"),
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[Suggestion]:
        result = await self._session.execute(select(Suggestion).where(Suggestion.trend_request_id == trend_request_id))
        return list(result.scalars().all())
