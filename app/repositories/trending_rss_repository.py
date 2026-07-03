import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trending_rss import TrendingRss
from app.utils.time import utc_now


class TrendingRssRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        geo: str,
        records: list[dict[str, Any]],
    ) -> list[TrendingRss]:
        entities = []
        now = utc_now()
        for record in records:
            entity = TrendingRss(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                title=record["title"],
                traffic=record.get("traffic"),
                description=record.get("description"),
                pub_date=record.get("pub_date"),
                link=record.get("link"),
                articles=record.get("articles"),
                article_count=record.get("article_count"),
                geo=geo,
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[TrendingRss]:
        result = await self._session.execute(
            select(TrendingRss).where(TrendingRss.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
