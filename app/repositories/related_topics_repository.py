import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.related_topic import RelatedTopic
from app.utils.time import utc_now


class RelatedTopicsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        records: dict[str, list[dict[str, Any]]],
    ) -> list[RelatedTopic]:
        entities = []
        now = utc_now()
        for topic_type, items in records.items():
            for item in items:
                entity = RelatedTopic(
                    id=uuid.uuid4(),
                    trend_request_id=trend_request_id,
                    keyword=keyword,
                    topic=item["topic"],
                    topic_type=topic_type,
                    topic_mid=item.get("mid"),
                    value=item.get("value"),
                    created_at=now,
                )
                entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[RelatedTopic]:
        result = await self._session.execute(
            select(RelatedTopic).where(RelatedTopic.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
