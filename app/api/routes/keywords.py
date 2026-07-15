from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_keywords_data_service
from app.core.exceptions import (
    DataForSEOClientError,
    DataForSEORateLimitError,
    DataForSEOTimeoutError,
)
from app.schemas.requests import KeywordsForKeywordsRequest, SearchVolumeRequest
from app.schemas.responses import (
    ErrorResponse,
    IngestionRunResponse,
    KeywordsForKeywordsResponse,
    SearchVolumeResponse,
    TrendRequestResponse,
)
from app.services.keywords_data_service import KeywordsDataService

router = APIRouter()


@router.post(
    "/search-volume",
    response_model=SearchVolumeResponse,
    responses={429: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Google Ads Search Volume",
    description="Fetches Google Ads average monthly search volume, competition and CPC for up to 1000 keywords "
    "at one location via DataForSEO, and persists it.",
)
async def search_volume(
    request: SearchVolumeRequest,
    service: KeywordsDataService = Depends(get_keywords_data_service),
) -> SearchVolumeResponse:
    try:
        return await service.collect_search_volume(request)
    except DataForSEORateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except DataForSEOTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except DataForSEOClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/keywords-for-keywords",
    response_model=KeywordsForKeywordsResponse,
    responses={429: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    summary="Collect Google Ads Keywords-for-Keywords",
    description="Expands up to 20 seed keywords into related keywords with Google Ads metrics via DataForSEO, "
    "and persists them.",
)
async def keywords_for_keywords(
    request: KeywordsForKeywordsRequest,
    service: KeywordsDataService = Depends(get_keywords_data_service),
) -> KeywordsForKeywordsResponse:
    try:
        return await service.collect_keywords_for_keywords(request)
    except DataForSEORateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except DataForSEOTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except DataForSEOClientError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/requests/{trend_request_id}",
    response_model=TrendRequestResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get Request Details",
    description="Returns a stored keyword-data request with its associated normalized records.",
)
async def get_trend_request(
    trend_request_id: UUID,
    service: KeywordsDataService = Depends(get_keywords_data_service),
) -> TrendRequestResponse:
    result = await service.get_trend_request(trend_request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Request not found")
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
    service: KeywordsDataService = Depends(get_keywords_data_service),
) -> IngestionRunResponse:
    result = await service.get_ingestion_run(ingestion_run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return IngestionRunResponse(**result)
