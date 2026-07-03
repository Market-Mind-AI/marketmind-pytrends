from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.trends_service import TrendsService


async def get_trends_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[TrendsService, None]:
    yield TrendsService(session)
