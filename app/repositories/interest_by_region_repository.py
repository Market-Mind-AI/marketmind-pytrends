import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.interest_by_region import InterestByRegion
from app.utils.time import utc_now


class InterestByRegionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        country: str,
        records: list[dict[str, Any]],
    ) -> list[InterestByRegion]:
        entities = []
        now = utc_now()
        for record in records:
            entity = InterestByRegion(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=keyword,
                country=country,
                region=record["region"],
                interest_value=record["value"],
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[InterestByRegion]:
        result = await self._session.execute(
            select(InterestByRegion).where(InterestByRegion.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
