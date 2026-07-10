from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestInfo(BaseModel):
    keyword: str
    country: str
    timeframe: str | None = None
    language: str


class Metadata(BaseModel):
    provider: str = "Google Trends"
    library: str = "PyTrends"
    endpoint: str
    execution_time_ms: int
    records: int
    stored: bool = True
    ingestion_run_id: UUID
    trend_request_id: UUID
    status: str
    collected_at: datetime


class InterestOverTimeItem(BaseModel):
    date: str
    value: int | float
    is_partial: bool = False


class InterestOverTimeData(BaseModel):
    interest_over_time: list[InterestOverTimeItem]


class InterestOverTimeResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: InterestOverTimeData

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request": {
                        "keyword": "air fryer",
                        "country": "ES",
                        "timeframe": "today 12-m",
                        "language": "en-US",
                    },
                    "metadata": {
                        "provider": "Google Trends",
                        "library": "PyTrends",
                        "endpoint": "interest_over_time",
                        "execution_time_ms": 512,
                        "records": 52,
                        "stored": True,
                        "ingestion_run_id": "550e8400-e29b-41d4-a716-446655440000",
                        "trend_request_id": "550e8400-e29b-41d4-a716-446655440001",
                        "status": "success",
                        "collected_at": "2026-06-29T10:00:00Z",
                    },
                    "data": {"interest_over_time": [{"date": "2025-06-01", "value": 54, "is_partial": False}]},
                }
            ]
        }
    }


class RegionItem(BaseModel):
    region: str
    value: int | float


class InterestByRegionData(BaseModel):
    regions: list[RegionItem]


class InterestByRegionResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: InterestByRegionData


class CountryItem(BaseModel):
    country: str
    value: int | float


class InterestByCountryData(BaseModel):
    countries: list[CountryItem]


class InterestByCountryResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: InterestByCountryData


class QueryItem(BaseModel):
    query: str
    value: int | float | None = None


class RelatedQueriesData(BaseModel):
    top: list[QueryItem]
    rising: list[QueryItem]


class RelatedQueriesResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: RelatedQueriesData


class TopicItem(BaseModel):
    topic: str
    mid: str | None = None
    value: int | float | None = None


class RelatedTopicsData(BaseModel):
    top: list[TopicItem]
    rising: list[TopicItem]


class RelatedTopicsResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: RelatedTopicsData


class SuggestionItem(BaseModel):
    title: str
    type: str | None = None
    mid: str | None = None


class SuggestionsData(BaseModel):
    suggestions: list[SuggestionItem]


class SuggestionsResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: SuggestionsData


class TrendingRssArticle(BaseModel):
    title: str | None = None
    url: str | None = None
    source: str | None = None
    snippet: str | None = None


class TrendingRssItem(BaseModel):
    title: str
    traffic: int | None = None
    description: str | None = None
    pub_date: str | None = None
    link: str | None = None
    articles: list[TrendingRssArticle] = Field(default_factory=list)
    article_count: int | None = None


class TrendingRssData(BaseModel):
    trends: list[TrendingRssItem]


class TrendingRssResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: TrendingRssData


class CategoriesResponse(BaseModel):
    request: RequestInfo
    metadata: Metadata
    data: dict


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
    request_payload: dict
    error_message: str | None = None
    created_at: datetime


class TrendRequestDetailItem(BaseModel):
    date: str | None = None
    value: int | float | None = None
    is_partial: bool | None = None
    region: str | None = None
    query: str | None = None
    query_type: str | None = None
    topic: str | None = None
    topic_type: str | None = None
    topic_mid: str | None = None
    title: str | None = None
    type: str | None = None
    mid: str | None = None


class TrendRequestResponse(BaseModel):
    id: UUID
    ingestion_run_id: UUID
    keyword: str
    country: str
    language: str | None = None
    timeframe: str | None = None
    endpoint: str
    created_at: datetime
    data: list[TrendRequestDetailItem] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
    ingestion_run_id: UUID | None = None
