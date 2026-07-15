from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    provider: str = "Google Ads"
    library: str = "DataForSEO"
    endpoint: str
    execution_time_ms: int
    records: int
    stored: bool = True
    ingestion_run_id: UUID
    trend_request_id: UUID
    status: str
    collected_at: datetime


class MonthlySearchItem(BaseModel):
    year: int | None = None
    month: int | None = None
    search_volume: int | None = None


class SearchVolumeRequestInfo(BaseModel):
    location: str
    language: str
    keywords: list[str]


class SearchVolumeItem(BaseModel):
    keyword: str
    search_volume: int | float | None = None
    competition: str | None = None
    competition_index: int | None = None
    cpc: float | None = None
    monthly_searches: list[MonthlySearchItem] = Field(default_factory=list)


class SearchVolumeData(BaseModel):
    keywords: list[SearchVolumeItem]


class SearchVolumeResponse(BaseModel):
    request: SearchVolumeRequestInfo
    metadata: Metadata
    data: SearchVolumeData


class KeywordsForKeywordsRequestInfo(BaseModel):
    location: str
    language: str
    seed_keywords: list[str]
    limit: int | None = None


class RelatedKeywordItem(BaseModel):
    seed_keyword: str
    keyword: str
    search_volume: int | float | None = None
    competition_index: int | None = None
    cpc: float | None = None
    monthly_searches: list[MonthlySearchItem] = Field(default_factory=list)


class KeywordsForKeywordsData(BaseModel):
    keywords: list[RelatedKeywordItem]


class KeywordsForKeywordsResponse(BaseModel):
    request: KeywordsForKeywordsRequestInfo
    metadata: Metadata
    data: KeywordsForKeywordsData


class HealthResponse(BaseModel):
    status: str
    database: str
    app_name: str
    environment: str


class IngestionRunResponse(BaseModel):
    id: UUID
    source: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    execution_time_ms: int | None = None
    request_payload: dict[str, Any]
    error_message: str | None = None
    created_at: datetime


class TrendRequestResponse(BaseModel):
    id: UUID
    ingestion_run_id: UUID
    keyword: str
    country: str
    language: str | None = None
    timeframe: str | None = None
    endpoint: str
    created_at: datetime
    data: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
    ingestion_run_id: UUID | None = None
