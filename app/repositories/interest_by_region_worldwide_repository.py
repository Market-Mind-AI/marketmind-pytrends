import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.interest_by_region_worldwide import InterestByRegionWorldwide
from app.utils.time import utc_now


class InterestByRegionWorldwideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        records: list[dict[str, Any]],
    ) -> list[InterestByRegionWorldwide]:
        entities = []
        now = utc_now()
        for record in records:
            entity = InterestByRegionWorldwide(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=keyword,
                country=record["country"],
                region_code=record["region_code"],
                region_name=record["region_name"],
                term=record["term"],
                term_language=record["term_language"],
                interest_value=record["value"],
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[InterestByRegionWorldwide]:
        result = await self._session.execute(
            select(InterestByRegionWorldwide).where(InterestByRegionWorldwide.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
