"""Google Ads API keyword-data client — the first source asked, DataForSEO the last.

DataForSEO resells exactly this: its Google Ads endpoints call the Keyword
Planner and add a markup and ten to twenty seconds. Measured on 02/11/2026 with
the BeProfit manager account, for fifteen air fryer terms in Spain, Portugal and
Romania: every monthly average identical to what DataForSEO had stored, the
same twelve-month series, half a second per country instead of nine, and the
related keywords of Spain (3,166) in 2.5 seconds instead of twelve to sixteen.
The Keyword Planner is not billed per call.

Two methods with the shapes of DataForSEOClient's, so the service can try this
one and fall back to the other without either side knowing which answered:

    search_volume          generateKeywordHistoricalMetrics
    keywords_for_keywords  generateKeywordIdeas (seed keywords, every page)

REST over the standard library, synchronous like the DataForSEO SDK the service
already runs in a worker thread. The official client library would bring gRPC
and protobuf for two POSTs.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.clients.dataforseo_locations import UNSUPPORTED_ISO2
from app.core.config import settings
from app.core.exceptions import GoogleAdsClientError, GoogleAdsTransientError
from app.core.logging import logger
from app.utils.retry import backoff_seconds, is_retryable_status

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API = "https://googleads.googleapis.com"

SEARCH_VOLUME_ENDPOINT = "google_ads_api_historical_metrics"
KEYWORDS_FOR_KEYWORDS_ENDPOINT = "google_ads_api_keyword_ideas"

_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "JANUARY",
            "FEBRUARY",
            "MARCH",
            "APRIL",
            "MAY",
            "JUNE",
            "JULY",
            "AUGUST",
            "SEPTEMBER",
            "OCTOBER",
            "NOVEMBER",
            "DECEMBER",
        ),
        start=1,
    )
}

# The same dialect gap the DataForSEO client documents: the rest of the system
# writes ISO 639-1, Google Ads keeps `iw` for Hebrew and splits Chinese.
_CODIGO_GOOGLE_ADS: dict[str, str] = {"he": "iw", "zh": "zh_CN"}
_CHINES_TRADICIONAL = {"TW", "HK", "MO"}

# Countries and languages Google Ads targets, read from the API once per process.
_PAISES: dict[str, int] | None = None
_IDIOMAS: dict[str, int] | None = None
_TOKEN: tuple[str, float] | None = None


def configured() -> bool:
    """Whether there is enough to ask Google Ads at all. Without it the service
    goes straight to DataForSEO, as it did before this client existed."""
    return bool(
        settings.google_ads_developer_token
        and settings.google_ads_client_id
        and settings.google_ads_client_secret
        and settings.google_ads_refresh_token
        and settings.google_ads_customer_id
    )


def _opt_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _monthly_searches(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """{year, month, search_volume}, newest first — the order DataForSEO stores,
    so a row reads the same whichever source wrote it."""
    items = [
        {
            "year": _opt_int(entry.get("year")),
            "month": _MONTHS.get(str(entry.get("month"))),
            "search_volume": _opt_int(entry.get("monthlySearches")),
        }
        for entry in raw or []
    ]
    items = [i for i in items if i["year"] is not None and i["month"] is not None]
    return sorted(items, key=lambda i: (i["year"], i["month"]), reverse=True)


def _record(text: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """One keyword in the per-keyword shape DataForSEOClient returns. `cpc` is
    the average cost per click in the account currency, which is what
    DataForSEO's `cpc` carries; `competition` is LOW/MEDIUM/HIGH in both."""
    cpc_micros = metrics.get("averageCpcMicros")
    competicao = metrics.get("competition")
    return {
        "keyword": text,
        "search_volume": _opt_int(metrics.get("avgMonthlySearches")),
        "competition": None if competicao in (None, "UNSPECIFIED", "UNKNOWN") else competicao,
        "competition_index": _opt_int(metrics.get("competitionIndex")),
        "cpc": None if cpc_micros is None else int(cpc_micros) / 1_000_000,
        "monthly_searches": _monthly_searches(metrics.get("monthlySearchVolumes")),
    }


class GoogleAdsClient:
    def _access_token(self) -> str:
        global _TOKEN
        if _TOKEN is not None and _TOKEN[1] > time.monotonic() + 60:
            return _TOKEN[0]
        body = urllib.parse.urlencode(
            {
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "refresh_token": settings.google_ads_refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode()
        try:
            with urllib.request.urlopen(_TOKEN_URL, body, timeout=settings.google_ads_timeout_seconds) as r:
                answer = json.load(r)
        except urllib.error.HTTPError as exc:
            # A refused refresh token is not passing: it will be refused again.
            raise GoogleAdsClientError(f"Google OAuth refused the refresh token: {exc.read()[:300]!r}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GoogleAdsTransientError(f"Google OAuth unreachable: {exc}") from exc
        _TOKEN = (answer["access_token"], time.monotonic() + int(answer.get("expires_in", 3600)))
        return _TOKEN[0]

    def _post(self, path: str, payload: dict[str, Any], label: str) -> dict[str, Any]:
        """One call, insisting a little on a passing failure. A little: past
        it, DataForSEO answers in this one's place, so waiting out a long
        backoff here would only make the fallback slower."""
        url = f"{_API}/{settings.google_ads_api_version}/customers/{settings.google_ads_customer_id}{path}"
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "developer-token": settings.google_ads_developer_token,
            "Content-Type": "application/json",
        }
        if settings.google_ads_login_customer_id:
            headers["login-customer-id"] = settings.google_ads_login_customer_id
        attempts = settings.google_ads_retries
        last: GoogleAdsTransientError | None = None
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(url, json.dumps(payload).encode(), headers)
            retry_after: str | None = None
            try:
                with urllib.request.urlopen(request, timeout=settings.google_ads_timeout_seconds) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                detail = exc.read()[:600].decode("utf-8", "replace")
                if not is_retryable_status(exc.code):
                    raise GoogleAdsClientError(f"Google Ads API {exc.code} for {label}: {detail}") from exc
                last = GoogleAdsTransientError(f"Google Ads API {exc.code} for {label}: {detail}")
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = GoogleAdsTransientError(f"Google Ads API unreachable for {label}: {exc}")
            logger.warning(f"Google Ads attempt {attempt}/{attempts} failed for {label}: {last}")
            if attempt < attempts:
                time.sleep(backoff_seconds(attempt, retry_after))
        raise last or GoogleAdsTransientError(f"Google Ads API failed for {label}")

    def _search(self, query: str, label: str) -> list[dict[str, Any]]:
        linhas: list[dict[str, Any]] = []
        payload: dict[str, Any] = {"query": query}
        while True:
            resposta = self._post("/googleAds:search", payload, label)
            linhas.extend(resposta.get("results", []))
            if not resposta.get("nextPageToken"):
                return linhas
            payload = {"query": query, "pageToken": resposta["nextPageToken"]}

    def _pais(self, country: str) -> int:
        """The geo target constant of the country, read from Google Ads once."""
        global _PAISES
        if country in UNSUPPORTED_ISO2:
            raise GoogleAdsClientError(
                f"Country '{country}' is not available for Google Ads demand: {UNSUPPORTED_ISO2[country]}"
            )
        if _PAISES is None:
            linhas = self._search(
                "SELECT geo_target_constant.id, geo_target_constant.country_code FROM geo_target_constant "
                "WHERE geo_target_constant.target_type = 'Country' AND geo_target_constant.status = 'ENABLED'",
                "geo target constants",
            )
            _PAISES = {
                linha["geoTargetConstant"]["countryCode"]: int(linha["geoTargetConstant"]["id"])
                for linha in linhas
                if linha.get("geoTargetConstant", {}).get("countryCode")
            }
            logger.info(f"Países do Google Ads carregados: {len(_PAISES)}")
        if country not in _PAISES:
            raise GoogleAdsClientError(f"Google Ads does not target country '{country}'")
        return _PAISES[country]

    def _idioma(self, language: str, country: str) -> int:
        """The language constant Google Ads uses for this language here."""
        global _IDIOMAS
        codigo = language.strip()
        if codigo.lower() == "zh" and country in _CHINES_TRADICIONAL:
            codigo = "zh_TW"
        codigo = _CODIGO_GOOGLE_ADS.get(codigo.lower(), codigo)
        if _IDIOMAS is None:
            linhas = self._search(
                "SELECT language_constant.id, language_constant.code FROM language_constant "
                "WHERE language_constant.targetable = TRUE",
                "language constants",
            )
            _IDIOMAS = {linha["languageConstant"]["code"]: int(linha["languageConstant"]["id"]) for linha in linhas}
            logger.info(f"Idiomas do Google Ads carregados: {len(_IDIOMAS)}")
        if codigo not in _IDIOMAS:
            raise GoogleAdsClientError(f"Google Ads does not offer language '{language}' (sent as '{codigo}')")
        return _IDIOMAS[codigo]

    def _alvo(self, country: str, language: str) -> dict[str, Any]:
        return {
            "language": f"languageConstants/{self._idioma(language, country)}",
            "geoTargetConstants": [f"geoTargetConstants/{self._pais(country)}"],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            # Without it the average CPC does not come back at all, and the
            # scoring service reads it as a purchase-intent signal.
            "historicalMetricsOptions": {"includeAverageCpc": True},
        }

    def search_volume(
        self, keywords: list[str], country: str, language: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Monthly average and twelve-month series for each keyword at ONE
        location. Returns (per-keyword dicts, request_payload)."""
        label = f"search_volume {keywords!r} in '{country}'"
        alvo = self._alvo(country, language)
        resposta = self._post(":generateKeywordHistoricalMetrics", {"keywords": list(keywords), **alvo}, label)
        registros = [_record(r["text"], r.get("keywordMetrics") or {}) for r in resposta.get("results", [])]
        logger.info(f"GOOGLE_ADS endpoint=search_volume country={country} results={len(registros)}")
        payload = {
            "keywords": list(keywords),
            "country": country,
            "language": language,
            **alvo,
            "provider": "google_ads_api",
            "endpoint": SEARCH_VOLUME_ENDPOINT,
        }
        return registros, payload

    def keywords_for_keywords(
        self, seed_keywords: list[str], country: str, language: str, limit: int | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """The keywords Google relates to the seed set at ONE location, every
        page of them. Each carries `seed_keyword`, the joined seed set, like
        DataForSEO's — it is what the stored rows are read back by."""
        label = f"keywords_for_keywords {seed_keywords!r} in '{country}'"
        alvo = self._alvo(country, language)
        corpo: dict[str, Any] = {"keywordSeed": {"keywords": list(seed_keywords)}, "pageSize": 10000, **alvo}
        seed_label = ", ".join(seed_keywords)
        registros: list[dict[str, Any]] = []
        while True:
            resposta = self._post(":generateKeywordIdeas", corpo, label)
            for r in resposta.get("results", []):
                registro = _record(r["text"], r.get("keywordIdeaMetrics") or {})
                registro["seed_keyword"] = seed_label
                registros.append(registro)
            if not resposta.get("nextPageToken") or (limit is not None and len(registros) >= limit):
                break
            corpo = {**corpo, "pageToken": resposta["nextPageToken"]}
        if limit is not None:
            registros = registros[:limit]
        logger.info(f"GOOGLE_ADS endpoint=keywords_for_keywords country={country} results={len(registros)}")
        payload = {
            "seed_keywords": list(seed_keywords),
            "country": country,
            "language": language,
            **alvo,
            "limit": limit,
            "provider": "google_ads_api",
            "endpoint": KEYWORDS_FOR_KEYWORDS_ENDPOINT,
        }
        return registros, payload
