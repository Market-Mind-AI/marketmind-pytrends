class PyTrendsClientError(Exception):
    pass


class PyTrendsTimeoutError(PyTrendsClientError):
    pass


class PyTrendsRateLimitError(PyTrendsClientError):
    pass


class PyTrendsEmptyResponseError(Exception):
    pass


class DataForSEOClientError(Exception):
    """The DataForSEO fallback itself failed — no further fallback exists,
    this propagates to the caller as a hard failure."""


class IngestionError(Exception):
    pass
