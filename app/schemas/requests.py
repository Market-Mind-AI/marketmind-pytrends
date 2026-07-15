from pydantic import BaseModel, Field

from app.core.config import settings


class SearchVolumeRequest(BaseModel):
    location: str = Field(
        ..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$", description="ISO-2 country code", examples=["ES"]
    )
    language: str = Field(default=settings.default_hl, description="Language code", examples=["en-US"])
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Keywords to fetch Google Ads search volume for (1..1000)",
        examples=[["air fryer", "robot vacuum"]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "location": "ES",
                    "language": "en-US",
                    "keywords": ["air fryer", "robot vacuum"],
                }
            ]
        }
    }


class KeywordsForKeywordsRequest(BaseModel):
    location: str = Field(
        ..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$", description="ISO-2 country code", examples=["ES"]
    )
    language: str = Field(default=settings.default_hl, description="Language code", examples=["en-US"])
    seed_keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Seed keywords to expand into related keywords (1..20)",
        examples=[["air fryer"]],
    )
    limit: int | None = Field(
        default=None, ge=1, description="Optional cap on the number of related keywords returned", examples=[100]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "location": "ES",
                    "language": "en-US",
                    "seed_keywords": ["air fryer"],
                    "limit": 100,
                }
            ]
        }
    }
