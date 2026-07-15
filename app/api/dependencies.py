from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.keywords_data_service import KeywordsDataService


async def get_keywords_data_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[KeywordsDataService, None]:
    yield KeywordsDataService(session)
