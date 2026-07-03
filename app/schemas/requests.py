from pydantic import BaseModel, Field

from app.core.config import settings


class TrendRequest(BaseModel):
    keyword: str = Field(..., min_length=2, description="Search keyword", examples=["air fryer"])
    country: str = Field(
        ..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$", description="ISO-2 country code", examples=["ES"]
    )
    timeframe: str = Field(
        default=settings.default_timeframe, description="Google Trends timeframe", examples=["today 12-m"]
    )
    language: str = Field(default=settings.default_hl, description="Language code", examples=["en-US"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "keyword": "air fryer",
                    "country": "ES",
                    "timeframe": "today 12-m",
                    "language": "en-US",
                }
            ]
        }
    }


class TrendingRssRequest(BaseModel):
    geo: str = Field(
        ..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$", description="ISO-2 country code", examples=["US"]
    )
    max_articles: int = Field(default=5, ge=0, le=20, description="Max articles per trend", examples=[5])
    language: str = Field(default=settings.default_hl, description="Language code", examples=["en-US"])

    model_config = {"json_schema_extra": {"examples": [{"geo": "US", "max_articles": 5, "language": "en-US"}]}}


class SuggestionRequest(BaseModel):
    keyword: str = Field(..., min_length=2, description="Search keyword", examples=["air fryer"])
    language: str = Field(default=settings.default_hl, description="Language code", examples=["en-US"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "keyword": "air fryer",
                    "language": "en-US",
                }
            ]
        }
    }
