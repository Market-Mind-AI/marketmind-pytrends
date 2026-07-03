from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.trends import router as trends_router
from app.core.config import settings
from app.core.logging import logger
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    await engine.dispose()
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title="MarketMind PyTrends API",
    description=(
        "Microservice for collecting, normalizing and persisting Google Trends data. "
        "This service does NOT calculate MOS, Entropy Weight, TOPSIS, or use LLMs. "
        "It exclusively collects raw Google Trends data via PyTrends, normalizes it, "
        "and stores it in PostgreSQL for auditing, traceability and future analysis."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, tags=["Health"])
app.include_router(trends_router, tags=["Trends"])
