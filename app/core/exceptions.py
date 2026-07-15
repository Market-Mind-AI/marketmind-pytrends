class DataForSEOClientError(Exception):
    """A DataForSEO Google Ads request failed — propagates to the caller as a
    hard failure (mapped to HTTP 502 by the routes)."""


class DataForSEORateLimitError(DataForSEOClientError):
    """DataForSEO rejected the request with a rate-limit status (mapped to 429)."""


class DataForSEOTimeoutError(DataForSEOClientError):
    """The DataForSEO request timed out (mapped to 504)."""


class IngestionError(Exception):
    pass
