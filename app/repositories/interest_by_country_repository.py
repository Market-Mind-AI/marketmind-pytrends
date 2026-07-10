import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.interest_by_country import InterestByCountry
from app.utils.time import utc_now


class InterestByCountryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        records: list[dict[str, Any]],
    ) -> list[InterestByCountry]:
        entities = []
        now = utc_now()
        for record in records:
            entity = InterestByCountry(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=keyword,
                country=record["country"],
                term=record["term"],
                term_language=record["term_language"],
                interest_value=record["value"],
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[InterestByCountry]:
        result = await self._session.execute(
            select(InterestByCountry).where(InterestByCountry.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
