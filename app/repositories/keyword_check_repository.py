import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.keyword_check import KeywordCheck
from app.utils.time import utc_now


def _normalized(keywords: list[str]) -> list[str]:
    # Em minúsculas porque a DataForSEO guarda os termos assim: um termo curado
    # com maiúsculas nunca casaria com o que foi coletado.
    return sorted({k.strip().lower() for k in keywords if k.strip()})


class KeywordCheckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, *, trend_request_id: uuid.UUID, location: str, keywords: list[str]) -> None:
        """Registra que a DataForSEO respondeu sobre estes termos agora.

        Chamado só depois de a tarefa voltar com sucesso: um termo de uma
        coleta que falhou não foi respondido, e não conta como verificado.
        """
        termos = _normalized(keywords)
        if not termos:
            return
        now = utc_now()
        stmt = insert(KeywordCheck).values(
            [
                {
                    "id": uuid.uuid4(),
                    "location": location,
                    "keyword": termo,
                    "trend_request_id": trend_request_id,
                    "checked_at": now,
                }
                for termo in termos
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_keyword_checks_location_keyword",
            set_={"checked_at": stmt.excluded.checked_at, "trend_request_id": stmt.excluded.trend_request_id},
        )
        await self._session.execute(stmt)

    async def last_checks(self, *, location: str, keywords: list[str]) -> dict[str, datetime]:
        """Termo em minúsculas -> quando foi respondido pela última vez."""
        termos = _normalized(keywords)
        if not termos:
            return {}
        stmt = (
            select(KeywordCheck.keyword, KeywordCheck.checked_at)
            .where(KeywordCheck.location == location)
            .where(KeywordCheck.keyword.in_(termos))
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
