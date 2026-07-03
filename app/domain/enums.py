from enum import StrEnum


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TrendEndpoint(StrEnum):
    INTEREST_OVER_TIME = "interest_over_time"
    INTEREST_BY_REGION = "interest_by_region"
    RELATED_QUERIES = "related_queries"
    RELATED_TOPICS = "related_topics"
    SUGGESTIONS = "suggestions"
    TRENDING_RSS = "trending_rss"
    CATEGORIES = "categories"


class QueryType(StrEnum):
    TOP = "top"
    RISING = "rising"


class TopicType(StrEnum):
    TOP = "top"
    RISING = "rising"
