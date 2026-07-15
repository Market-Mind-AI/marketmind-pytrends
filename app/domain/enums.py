from enum import StrEnum


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class KeywordEndpoint(StrEnum):
    SEARCH_VOLUME = "search_volume"
    KEYWORDS_FOR_KEYWORDS = "keywords_for_keywords"
