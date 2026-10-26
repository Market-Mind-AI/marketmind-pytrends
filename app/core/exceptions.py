class DataForSEOClientError(Exception):
    """A DataForSEO respondeu, e a resposta não serve: um 4xx que não é de
    espera, uma tarefa recusada (4xxxx), um país ou idioma que o Google Ads não
    oferece. Repetir não muda a resposta, então não se repete (502)."""


class DataForSEOTransientError(Exception):
    """A DataForSEO (ou o Google atrás dela) está ocupada ou fora do ar -- 5xx,
    429, 408, timeout, rede, tarefa 5xxxx -- e continuou assim depois de todas
    as tentativas. 503 em todos os coletores: quer dizer "tente de novo mais
    tarde", que é exatamente o que vale fazer.

    Até 26/10/2026 esta família herdava de DataForSEOClientError e saía como
    502 (ou 429, ou 504), enquanto os outros coletores respondiam 503 à mesma
    situação."""


class DataForSEORateLimitError(DataForSEOTransientError):
    """DataForSEO rejected the request with a rate-limit status (429)."""


class DataForSEOTimeoutError(DataForSEOTransientError):
    """The DataForSEO request timed out (408/504)."""


class DataForSEOTransientTaskError(DataForSEOTransientError):
    """DataForSEO returned HTTP 200 but the *task* failed with a server-side
    status code (5xxxx) — e.g. 50301 when Google's OAuth endpoint momentarily
    returns 503. Distinct from client-side task errors (4xxxx, permanent) so the
    retry loop can retry these transient upstream failures instead of aborting a
    whole analysis on a single blip."""
