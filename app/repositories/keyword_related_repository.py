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

    async def latest_by_seed(self, *, location: str, seed_keyword: str) -> list[KeywordRelated]:
        """The freshest stored related keyword per keyword, for one seed and location.

        One row per related keyword, most recently collected. The table keeps
        every collection, so without DISTINCT ON a keyword returned by three
        runs reaches the caller three times and is counted three times.

        Read from the latest collection of this seed only. Sorting every
        collection ever made to pick the freshest row per keyword meant
        sorting 70 thousand rows of monthly series for the air fryer in the
        US — 11.8 seconds, several times per analysis (29/10/2026). The latest
        collection IS the freshest answer for every keyword it returned, and a
        keyword Google stopped returning is one it no longer relates.
        """
        keyword = KeywordRelated.keyword
        ultima = (
            select(KeywordRelated.trend_request_id)
            .where(KeywordRelated.location == location)
            .where(KeywordRelated.seed_keyword == seed_keyword)
            .order_by(KeywordRelated.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(KeywordRelated)
            .where(KeywordRelated.trend_request_id == ultima)
            .distinct(keyword)
            .order_by(keyword, KeywordRelated.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
