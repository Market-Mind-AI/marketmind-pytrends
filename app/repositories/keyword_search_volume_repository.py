import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.keyword_search_volume import KeywordSearchVolume
from app.utils.time import utc_now


class KeywordSearchVolumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        trend_request_id: uuid.UUID,
        location: str,
        language: str,
        records: list[dict[str, Any]],
    ) -> list[KeywordSearchVolume]:
        entities = []
        now = utc_now()
        for record in records:
            entity = KeywordSearchVolume(
                id=uuid.uuid4(),
                trend_request_id=trend_request_id,
                keyword=record["keyword"],
                location=location,
                language=language,
                search_volume=record.get("search_volume"),
                competition=record.get("competition"),
                competition_index=record.get("competition_index"),
                cpc=record.get("cpc"),
                monthly_searches=record.get("monthly_searches"),
                created_at=now,
            )
            entities.append(entity)
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def get_by_trend_request_id(self, trend_request_id: uuid.UUID) -> list[KeywordSearchVolume]:
        result = await self._session.execute(
            select(KeywordSearchVolume).where(KeywordSearchVolume.trend_request_id == trend_request_id)
        )
        return list(result.scalars().all())

    async def latest_by_keywords(self, *, location: str, keywords: list[str]) -> list[KeywordSearchVolume]:
        """The freshest stored row per keyword for a location.

        Matched case-insensitively: DataForSEO stores keywords lowercased, so a
        curated term written with capitals would otherwise never match what was
        collected and would look missing forever, re-downloading every run at
        real cost.

        One row per keyword, the most recently collected one. The table keeps
        every collection, so without DISTINCT ON a keyword collected three times
        reaches the caller three times and gets counted three times.

        A keyword absent from the answer was never collected for this location.
        That absence is the useful part -- it is exactly what still needs
        fetching -- so it is left to the caller to read rather than padded with
        empty rows here.
        """
        if not keywords:
            return []
        lowered = [k.strip().lower() for k in keywords if k.strip()]
        if not lowered:
            return []

        lowered_keyword = func.lower(KeywordSearchVolume.keyword)
        stmt = (
            select(KeywordSearchVolume)
            .where(KeywordSearchVolume.location == location)
            .where(lowered_keyword.in_(lowered))
            .distinct(lowered_keyword)
            .order_by(lowered_keyword, KeywordSearchVolume.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
