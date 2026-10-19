class DataForSEOClientError(Exception):
    """A DataForSEO Google Ads request failed — propagates to the caller as a
    hard failure (mapped to HTTP 502 by the routes)."""


class DataForSEORateLimitError(DataForSEOClientError):
    """DataForSEO rejected the request with a rate-limit status (mapped to 429)."""


class DataForSEOTimeoutError(DataForSEOClientError):
    """The DataForSEO request timed out (mapped to 504)."""


class DataForSEOTransientTaskError(DataForSEOClientError):
    """DataForSEO returned HTTP 200 but the *task* failed with a server-side
    status code (5xxxx) — e.g. 50301 when Google's OAuth endpoint momentarily
    returns 503. Distinct from client-side task errors (4xxxx, permanent) so the
    retry loop can retry these transient upstream failures instead of aborting a
    whole analysis on a single blip."""
