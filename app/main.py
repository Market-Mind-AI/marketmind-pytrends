from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.keywords import router as keywords_router
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
    title="MarketMind Keywords Data API",
    description=(
        "Microservice for collecting, normalizing and persisting Google Ads keyword data via DataForSEO. "
        "This service does NOT calculate MOS, Rank Order Centroid, TOPSIS, or use LLMs. "
        "It exclusively collects raw Google Ads keyword metrics (search volume, competition, CPC, "
        "monthly searches and related keywords), and stores them in PostgreSQL for auditing, "
        "traceability and future analysis."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health_router, tags=["Health"])
app.include_router(keywords_router, tags=["Keywords"])
