from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns application status and database connectivity.",
)
async def health_check(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok",
        database=db_status,
        app_name=settings.app_name,
        environment=settings.app_env,
    )
