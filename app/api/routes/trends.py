from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_trends_service
from app.core.exceptions import (
    PyTrendsClientError,
    PyTrendsEmptyResponseError,
    PyTrendsRateLimitError,
    PyTrendsTimeoutError,
)
from app.schemas.requests import SuggestionRequest, TrendingRssRequest, TrendRequest, WorldwideTrendRequest
from app.schemas.responses import (
    CategoriesResponse,
    ErrorResponse,
    IngestionRunResponse,
    InterestByCountryResponse,
    InterestByRegionResponse,
    InterestOverTimeResponse,
    RelatedQueriesResponse,
    RelatedTopicsResponse,
    SuggestionsResponse,
    TrendingRssResponse,
    TrendRequestResponse,
)
from app.services.trends_service import TrendsService

router = APIRouter()


@router.post(
    "/interest-over-time",
    response_model=InterestOverTimeResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Interest Over Time",
    description="Fetches Google Trends interest over time data for a keyword, normalizes and persists it.",
)
async def interest_over_time(
    request: TrendRequest,
    service: TrendsService = Depends(get_trends_service),
) -> InterestOverTimeResponse:
    try:
        return await service.collect_interest_over_time(request)
    except PyTrendsEmptyResponseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/interest-by-region",
    response_model=InterestByRegionResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Interest By Region",
    description="Fetches Google Trends interest by region data for a keyword, normalizes and persists it.",
)
async def interest_by_region(
    request: TrendRequest,
    service: TrendsService = Depends(get_trends_service),
) -> InterestByRegionResponse:
    try:
        return await service.collect_interest_by_region(request)
    except PyTrendsEmptyResponseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/interest-by-country",
    response_model=InterestByCountryResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Interest By Country",
    description="Fetches worldwide Google Trends interest broken down by country for a keyword, "
    "normalizes and persists it.",
)
async def interest_by_country(
    request: WorldwideTrendRequest,
    service: TrendsService = Depends(get_trends_service),
) -> InterestByCountryResponse:
    try:
        return await service.collect_interest_by_country(request)
    except PyTrendsEmptyResponseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/related-queries",
    response_model=RelatedQueriesResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Related Queries",
    description="Fetches Google Trends related queries for a keyword, normalizes and persists them.",
)
async def related_queries(
    request: TrendRequest,
    service: TrendsService = Depends(get_trends_service),
) -> RelatedQueriesResponse:
    try:
        return await service.collect_related_queries(request)
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/related-topics",
    response_model=RelatedTopicsResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Related Topics",
    description="Fetches Google Trends related topics for a keyword, normalizes and persists them.",
)
async def related_topics(
    request: TrendRequest,
    service: TrendsService = Depends(get_trends_service),
) -> RelatedTopicsResponse:
    try:
        return await service.collect_related_topics(request)
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Suggestions",
    description="Fetches Google Trends keyword suggestions, normalizes and persists them.",
)
async def suggestions(
    request: SuggestionRequest,
    service: TrendsService = Depends(get_trends_service),
) -> SuggestionsResponse:
    try:
        return await service.collect_suggestions(request)
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/trending-rss",
    response_model=TrendingRssResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Trending RSS",
    description="Fetches real-time trending topics from Google Trends RSS feed with news articles.",
)
async def trending_rss(
    request: TrendingRssRequest,
    service: TrendsService = Depends(get_trends_service),
) -> TrendingRssResponse:
    try:
        return await service.collect_trending_rss(request)
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    responses={502: {"model": ErrorResponse}},
    summary="Get Google Trends Categories",
    description="Fetches the full category tree from Google Trends and persists the raw response.",
)
async def categories(
    language: str = "en-US",
    service: TrendsService = Depends(get_trends_service),
) -> CategoriesResponse:
    try:
        return await service.collect_categories(language)
    except PyTrendsRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PyTrendsTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PyTrendsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/requests/{trend_request_id}",
    response_model=TrendRequestResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get Trend Request Details",
    description="Returns a stored trend request with its associated normalized data.",
)
async def get_trend_request(
    trend_request_id: UUID,
    service: TrendsService = Depends(get_trends_service),
) -> TrendRequestResponse:
    result = await service.get_trend_request(trend_request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trend request not found")
    return TrendRequestResponse(**result)


@router.get(
    "/runs/{ingestion_run_id}",
    response_model=IngestionRunResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get Ingestion Run Details",
    description="Returns status and metadata of a specific ingestion run.",
)
async def get_ingestion_run(
    ingestion_run_id: UUID,
    service: TrendsService = Depends(get_trends_service),
) -> IngestionRunResponse:
    result = await service.get_ingestion_run(ingestion_run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return IngestionRunResponse(**result)
