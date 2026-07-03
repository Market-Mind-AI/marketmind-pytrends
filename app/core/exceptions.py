class PyTrendsClientError(Exception):
    pass


class PyTrendsTimeoutError(PyTrendsClientError):
    pass


class PyTrendsRateLimitError(PyTrendsClientError):
    pass


class PyTrendsEmptyResponseError(Exception):
    pass


class IngestionError(Exception):
    pass
