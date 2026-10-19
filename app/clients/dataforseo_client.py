"""DataForSEO Google Ads keyword-data client.

Collects Google Ads Search Volume and Keywords-for-Keywords data via the
official `dataforseo-client` SDK (sync — called directly from the async
service methods, matching this project's existing style of driving sync
clients from async code). Google Trends collection has been retired; this
client now targets the Google Ads endpoints (KeywordsDataApi.google_ads_*).

Sandbox vs Live is a plain host swap (settings.dataforseo_use_sandbox) — same
auth, same request/response shape; sandbox never bills and returns mock data
(see scripts/verify_dataforseo_locations.py for the same sandbox/live note).
"""

import time
from typing import Any

import urllib3
from dataforseo_client import api_client as dfs_api_provider
from dataforseo_client import configuration as dfs_config
from dataforseo_client.api.keywords_data_api import KeywordsDataApi
from dataforseo_client.models.keywords_data_google_ads_keywords_for_keywords_live_request_info import (
    KeywordsDataGoogleAdsKeywordsForKeywordsLiveRequestInfo,
)
from dataforseo_client.models.keywords_data_google_ads_search_volume_live_request_info import (
    KeywordsDataGoogleAdsSearchVolumeLiveRequestInfo,
)
from dataforseo_client.rest import ApiException

from app.clients.dataforseo_locations import ISO2_TO_LOCATION_NAME, UNSUPPORTED_ISO2
from app.core import spend
from app.core.config import settings
from app.core.exceptions import (
    DataForSEOClientError,
    DataForSEORateLimitError,
    DataForSEOTimeoutError,
    DataForSEOTransientTaskError,
)
from app.core.logging import logger

_SANDBOX_HOST = "https://sandbox.dataforseo.com"
# DataForSEO status codes are 20000-series for success, 40000+ for errors —
# same convention documented across their whole API.
_TASK_ERROR_THRESHOLD = 40000
# DataForSEO task-level status codes follow HTTP-like semantics: 4xxxx are
# client errors (bad params — permanent), 5xxxx are server-side errors
# (transient — e.g. 50301 when Google's OAuth endpoint momentarily returns 503).
# Retry the 5xxxx class the same way we retry HTTP 5xx gateway errors.
_TASK_SERVER_ERROR_THRESHOLD = 50000
_RATE_LIMIT_STATUS = 429
_TIMEOUT_STATUSES = frozenset({408, 504})
# Transient upstream/gateway errors worth retrying (DataForSEO returns 502 Bad
# Gateway under load — a burst of live calls across many countries triggers it).
# Retried with linear backoff before surfacing as an error (2026-07-15).
_TRANSIENT_STATUSES = frozenset({500, 502, 503, 504})

SEARCH_VOLUME_ENDPOINT = "google_ads_search_volume_live"
KEYWORDS_FOR_KEYWORDS_ENDPOINT = "google_ads_keywords_for_keywords_live"


def _opt_float(value: Any) -> float | None:
    """Coerce a DataForSEO numeric field to float, tolerating None/missing/
    unparseable values by returning None (the metric is simply unknown)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _opt_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _monthly_searches(raw: Any) -> list[dict[str, Any]]:
    """Normalize the trailing-12-months array into plain JSON-serializable
    dicts {year, month, search_volume}. None entries are skipped."""
    items: list[dict[str, Any]] = []
    for entry in raw or []:
        if entry is None:
            continue
        items.append(
            {
                "year": _opt_int(getattr(entry, "year", None)),
                "month": _opt_int(getattr(entry, "month", None)),
                "search_volume": _opt_int(getattr(entry, "search_volume", None)),
            }
        )
    return items


def _result_to_dict(item: Any) -> dict[str, Any]:
    """Flatten a Google Ads result item into the per-keyword shape shared by
    both endpoints. Missing numeric fields stay None (nullable in the DB)."""
    return {
        "keyword": _opt_str(getattr(item, "keyword", None)) or "",
        "search_volume": _opt_int(getattr(item, "search_volume", None)),
        "competition": _opt_str(getattr(item, "competition", None)),
        "competition_index": _opt_int(getattr(item, "competition_index", None)),
        "cpc": _opt_float(getattr(item, "cpc", None)),
        "monthly_searches": _monthly_searches(getattr(item, "monthly_searches", None)),
    }


# O catálogo de países da própria DataForSEO, buscado uma vez por processo.
#
# Era uma tabela escrita à mão com 25 países, e acrescentar um mercado exigia
# alguém editar o arquivo antes. Em 24/09/2026 isso derrubou uma análise da
# Bolívia inteira: o país estava no catálogo da DataForSEO, estava no seletor do
# front, e morria aqui com "No DataForSEO location_name mapping for country
# 'BO'". Cento e vinte e seis dos países recém-abertos falhariam igual.
#
# O endpoint de localizações é estático e NÃO é cobrado — é lista de referência,
# igual em sandbox e em produção. Então a pergunta é feita à fonte, que é quem
# sabe, e a tabela manual fica só de rede de segurança para quando a chamada
# não sair.
_CATALOGO: dict[str, str] | None = None

# O Google Ads fala um dialeto próprio de códigos de idioma, e o resto do
# sistema fala ISO 639-1 (é o que o LLM de enriquecimento escreve em
# `search_language`). Duas divergências conhecidas, medidas em 14/10/2026 com
# Israel e China: hebraico é `iw` (o código antigo, que o Google nunca
# abandonou) e chinês não existe sem a variante — `zh_CN` simplificado, `zh_TW`
# tradicional. Mandar `he` ou `zh` recebe "40501 Invalid Field: 'language_code'",
# e a análise inteira desiste depois de três tentativas iguais.
_CODIGO_GOOGLE_ADS: dict[str, str] = {"he": "iw", "zh": "zh_CN"}
_CHINES_TRADICIONAL = {"TW", "HK", "MO"}
# Os idiomas que a própria DataForSEO lista para o Google Ads, uma vez por
# processo — a rede de segurança é o mapa acima.
_IDIOMAS: set[str] | None = None


class DataForSEOClient:
    def _catalogo_de_paises(self) -> dict[str, str]:
        """ISO2 -> `location_name`, dito pela DataForSEO.

        Uma vez por processo. Só as entradas de PAÍS: a lista tem 2.311
        localizações e a maioria é subdivisão, então sem o filtro "Brazil" vira
        "State of Acre,Brazil" — foi o que já produziu 23 divergências falsas
        num script de verificação.
        """
        global _CATALOGO
        if _CATALOGO is not None:
            return _CATALOGO
        try:
            with dfs_api_provider.ApiClient(self._configuration()) as api_client:
                resposta = KeywordsDataApi(api_client).google_trends_locations()
            resultado = (resposta.tasks or [])[0].result or []
            _CATALOGO = {
                loc.country_iso_code: loc.location_name
                for loc in resultado
                if loc and loc.country_iso_code and getattr(loc, "location_type", None) == "Country"
            }
            logger.info(f"Catálogo de localizações da DataForSEO carregado: {len(_CATALOGO)} países")
        except Exception as exc:  # noqa: BLE001 — sem catálogo, a tabela estática ainda responde
            logger.warning(f"Não consegui ler o catálogo de localizações da DataForSEO: {exc}")
            _CATALOGO = {}
        return _CATALOGO

    def _catalogo_de_idiomas(self) -> set[str]:
        """Os `language_code` que o Google Ads aceita, ditos pela DataForSEO.
        Mesmo regime do catálogo de países: endpoint de referência, não
        cobrado, lido uma vez."""
        global _IDIOMAS
        if _IDIOMAS is not None:
            return _IDIOMAS
        try:
            with dfs_api_provider.ApiClient(self._configuration()) as api_client:
                resposta = KeywordsDataApi(api_client).google_ads_languages()
            resultado = (resposta.tasks or [])[0].result or []
            _IDIOMAS = {lang.language_code for lang in resultado if lang and lang.language_code}
            logger.info(f"Catálogo de idiomas do Google Ads carregado: {len(_IDIOMAS)} códigos")
        except Exception as exc:  # noqa: BLE001 — sem catálogo, o mapa estático ainda responde
            logger.warning(f"Não consegui ler o catálogo de idiomas do Google Ads: {exc}")
            _IDIOMAS = set()
        return _IDIOMAS

    def _language_code(self, language: str, country: str) -> str:
        """O código que o Google Ads aceita para este idioma neste país."""
        codigo = language.strip()
        if codigo.lower() == "zh" and country in _CHINES_TRADICIONAL:
            return "zh_TW"
        codigo = _CODIGO_GOOGLE_ADS.get(codigo.lower(), codigo)
        conhecidos = self._catalogo_de_idiomas()
        if conhecidos and codigo not in conhecidos:
            raise DataForSEOClientError(
                f"Google Ads does not offer language '{language}' (sent as '{codigo}') — it cannot be "
                "measured for demand"
            )
        return codigo

    def _location_name(self, country: str) -> str:
        if country in UNSUPPORTED_ISO2:
            raise DataForSEOClientError(
                f"Country '{country}' is not available for Google Ads demand: {UNSUPPORTED_ISO2[country]}"
            )
        # A fonte primeiro; a tabela escrita à mão é a rede de segurança.
        location_name = self._catalogo_de_paises().get(country) or ISO2_TO_LOCATION_NAME.get(country)
        if location_name is None:
            raise DataForSEOClientError(
                f"DataForSEO does not list country '{country}' at country level — it cannot be "
                "measured for Google Ads demand"
            )
        return location_name

    def _configuration(self) -> Any:
        host = _SANDBOX_HOST if settings.dataforseo_use_sandbox else None
        return dfs_config.Configuration(
            username=settings.dataforseo_login, password=settings.dataforseo_password, host=host
        )

    def _translate_api_exception(self, exc: ApiException, label: str) -> DataForSEOClientError:
        status = getattr(exc, "status", None)
        if status == _RATE_LIMIT_STATUS:
            return DataForSEORateLimitError(f"DataForSEO rate-limited request for {label}: {exc}")
        if status in _TIMEOUT_STATUSES:
            return DataForSEOTimeoutError(f"DataForSEO timed out for {label}: {exc}")
        return DataForSEOClientError(f"DataForSEO API error for {label}: {exc}")

    def _run_with_retry(self, call: Any, label: str) -> Any:
        """Run a DataForSEO API call, retrying transient upstream failures
        (502/503/504/500, timeouts, 429) with linear backoff. A burst of live
        calls across many countries makes DataForSEO's gateway return 502s;
        without this a single 502 aborts a whole MarketMind analysis (core has
        an all-or-nothing completeness gate). Non-transient errors are
        translated and raised immediately."""
        last_exc: ApiException | None = None
        for attempt in range(1, settings.default_retries + 1):
            try:
                return call()
            except ApiException as exc:
                status = getattr(exc, "status", None)
                transient = (
                    status in _TRANSIENT_STATUSES or status == _RATE_LIMIT_STATUS or status in _TIMEOUT_STATUSES
                )
                if not transient or attempt == settings.default_retries:
                    raise self._translate_api_exception(exc, label) from exc
                last_exc = exc
                logger.warning(
                    f"DataForSEO transient error (status={status}) for {label}; "
                    f"retry {attempt}/{settings.default_retries}"
                )
                time.sleep(settings.default_backoff * attempt)
            except (urllib3.exceptions.HTTPError, ConnectionError, TimeoutError, OSError) as exc:
                # Network-level failures (DNS resolution, connection reset, pool
                # timeouts) surface as raw urllib3/socket errors, NOT ApiException,
                # so the clause above never caught them — a single DNS blip
                # ('Failed to resolve api.dataforseo.com') killed a whole country
                # with zero retries and aborted the analysis. These are ALWAYS
                # transient: retry with the same linear backoff so the collector
                # self-heals instead of failing loudly (system-resilience premise).
                if attempt == settings.default_retries:
                    raise DataForSEOClientError(
                        f"DataForSEO network error for {label} after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    f"DataForSEO network error for {label}; retry {attempt}/{settings.default_retries}: {exc}"
                )
                time.sleep(settings.default_backoff * attempt)
            except DataForSEOTransientTaskError as exc:
                # HTTP 200 but the task failed with a 5xxxx server-side code
                # (e.g. 50301 — Google OAuth 503). Same transient treatment: a
                # single upstream blip must not abort the whole analysis.
                if attempt == settings.default_retries:
                    raise DataForSEOClientError(
                        f"DataForSEO task failed for {label} after {attempt} attempts: {exc}"
                    ) from exc
                logger.warning(
                    f"DataForSEO transient task error for {label}; "
                    f"retry {attempt}/{settings.default_retries}: {exc}"
                )
                time.sleep(settings.default_backoff * attempt)
        raise self._translate_api_exception(last_exc, label)  # pragma: no cover — loop always returns/raises above

    def _extract_results(self, response: Any, label: str) -> list[Any]:
        tasks = response.tasks or []
        if not tasks:
            raise DataForSEOClientError(f"DataForSEO returned no tasks for {label}")
        task = tasks[0]
        if task is None:
            raise DataForSEOClientError(f"DataForSEO returned an empty task for {label}")
        # What DataForSEO billed for this task, in USD, as it reports it —
        # logged, and added to the request's tally (app/core/spend.py) so the
        # scoring service can carry it into the analysis's trace. Before the
        # status check, since a failed task can be billed too.
        logger.info(
            f"DATAFORSEO_COST endpoint={label.split(' ', 1)[0]} cost_usd={task.cost} "
            f"status={task.status_code} results={task.result_count}"
        )
        spend.add(task.cost)
        if task.status_code is not None and task.status_code >= _TASK_ERROR_THRESHOLD:
            message = f"DataForSEO task failed ({task.status_code}): {task.status_message}"
            if task.status_code >= _TASK_SERVER_ERROR_THRESHOLD:
                # Server-side (5xxxx) — transient upstream blip; let the retry loop handle it.
                raise DataForSEOTransientTaskError(message)
            raise DataForSEOClientError(message)
        return [r for r in (task.result or []) if r is not None]

    def search_volume(
        self, keywords: list[str], country: str, language: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Google Ads Search Volume live for up to 1000 keywords at ONE
        location. Returns (per-keyword dicts, request_payload)."""
        location_name = self._location_name(country)
        language_code = self._language_code(language, country)
        label = f"search_volume {keywords!r} in '{country}'"
        request = KeywordsDataGoogleAdsSearchVolumeLiveRequestInfo(
            keywords=list(keywords),
            location_name=location_name,
            language_code=language_code,
        )
        payload: dict[str, Any] = {
            "keywords": list(keywords),
            "country": country,
            "location_name": location_name,
            "language_code": language_code,
            "provider": "dataforseo_google_ads",
            "endpoint": SEARCH_VOLUME_ENDPOINT,
        }
        def _do() -> Any:
            with dfs_api_provider.ApiClient(self._configuration()) as api_client:
                response = KeywordsDataApi(api_client).google_ads_search_volume_live([request])
            return self._extract_results(response, label)

        results = self._run_with_retry(_do, label)
        return [_result_to_dict(item) for item in results], payload

    def keywords_for_keywords(
        self, seed_keywords: list[str], country: str, language: str, limit: int | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Google Ads Keywords-for-Keywords live for up to 20 seed keywords at
        ONE location. Returns (related-keyword dicts, request_payload). Each
        related dict carries the same metric fields plus `seed_keyword` (the
        seed set that produced it). `limit` caps the returned rows client-side
        (the endpoint itself can return up to 20000)."""
        location_name = self._location_name(country)
        language_code = self._language_code(language, country)
        label = f"keywords_for_keywords {seed_keywords!r} in '{country}'"
        request = KeywordsDataGoogleAdsKeywordsForKeywordsLiveRequestInfo(
            keywords=list(seed_keywords),
            location_name=location_name,
            language_code=language_code,
        )
        payload: dict[str, Any] = {
            "seed_keywords": list(seed_keywords),
            "country": country,
            "location_name": location_name,
            "language_code": language_code,
            "limit": limit,
            "provider": "dataforseo_google_ads",
            "endpoint": KEYWORDS_FOR_KEYWORDS_ENDPOINT,
        }
        def _do() -> Any:
            with dfs_api_provider.ApiClient(self._configuration()) as api_client:
                response = KeywordsDataApi(api_client).google_ads_keywords_for_keywords_live([request])
            return self._extract_results(response, label)

        results = self._run_with_retry(_do, label)
        seed_label = ", ".join(seed_keywords)
        dicts: list[dict[str, Any]] = []
        for item in results:
            record = _result_to_dict(item)
            record["seed_keyword"] = seed_label
            dicts.append(record)
        if limit is not None:
            dicts = dicts[:limit]
        return dicts, payload
