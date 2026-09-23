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


class StoredSearchVolumeRequest(BaseModel):
    """A read, not a collection. Nothing is fetched from DataForSEO and nothing
    is billed.

    It is a POST because the keyword list is the same size as a collection's --
    up to a thousand terms -- and a thousand of them do not fit in a query
    string.
    """

    location: str = Field(
        ..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$", description="ISO-2 country code", examples=["ES"]
    )
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Keywords to look up in what is already stored (1..1000)",
        examples=[["air fryer", "freidora de aire"]],
    )
    stale_after_days: int | None = Field(
        None,
        ge=1,
        description=(
            "Um termo coletado há mais dias que isto entra em `missing`, mesmo tendo linha "
            "guardada. Sem este campo nada vence: era o comportamento antigo, em que um "
            "volume de busca coletado uma vez valia para sempre."
        ),
        examples=[30],
    )

    model_config = {
        "json_schema_extra": {"examples": [{"location": "ES", "keywords": ["air fryer", "freidora de aire"]}]}
    }
