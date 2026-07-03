import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.interest_over_time import InterestOverTime
from app.utils.time import utc_now


class InterestOverTimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        keyword: str,
        country: str,
        records: list[dict[str, Any]],
    ) -> list[InterestOverTime]:
        entities = []
        now = utc_now()
        for record in records:
            entity = InterestOverTime(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=keyword,
                country=country,
                date=date.fromisoformat(record["date"]),
                interest_value=record["value"],
                is_partial=record.get("is_partial", False),
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[InterestOverTime]:
        result = await self._session.execute(
            select(InterestOverTime).where(InterestOverTime.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())
