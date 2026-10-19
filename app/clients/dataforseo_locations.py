"""Static ISO2 -> DataForSEO `location_name` mapping for the Google Ads
keyword-data endpoints, scoped to the scoring service's reference basket
(same "canonical table built once, no LLM" philosophy already applied to
country-code de-para elsewhere in the project).

The catalogue it is checked against is DataForSEO's
`keywords_data/google_trends/locations` list — a leftover of the Google Trends
days (retired in migration 007) that is kept because the location names are
the same ones the Google Ads endpoints accept.

CONFIRMADO em 2026-09-22 contra a lista da própria DataForSEO
(`GET /v3/keywords_data/google_trends/locations`), com credencial real: as 24
entradas batem exatamente. Rode scripts/verify_dataforseo_locations.py antes de
acrescentar um país — ele confere a tabela e lista o que a DataForSEO cobre e
este projeto ainda não analisa (187 países em 2026-09-22).

Um aviso sobre esse script: ele já acusou 23 divergências que não existiam. A
lista tem 2.311 localizações e a maioria é subdivisão — sem filtrar por
`location_type == "Country"`, "Brazil" vira "State of Acre,Brazil".

Rússia e Belarus estão ausentes de fato: verificado em 2026-09-22, a DataForSEO
não os lista (sanções), então qualquer busca tem de falhar alto (ver
dataforseo_client.py) em vez de adivinhar um nome em silêncio.

A China é outro caso, e a diferença importa: ela ESTÁ no catálogo, listada como
'China'. A exclusão dela não é de cobertura — é que o Google é bloqueado na China
continental, então o volume de busca do Google Ads não representa aquele
mercado. Um número que existe e não significa nada é pior que um ausente, porque
entra na comparação.
"""

ISO2_TO_LOCATION_NAME: dict[str, str] = {
    "AR": "Argentina",
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "CL": "Chile",
    # China (CN) is intentionally NOT here — see UNSUPPORTED_ISO2 (Google is
    # blocked in mainland China, so Google Ads returns no representative volume).
    "CO": "Colombia",
    "FR": "France",
    "DE": "Germany",
    "IN": "India",
    "ID": "Indonesia",
    "IT": "Italy",
    "JP": "Japan",
    "MX": "Mexico",
    "NL": "Netherlands",
    "PE": "Peru",
    "PL": "Poland",
    "PT": "Portugal",
    "SA": "Saudi Arabia",
    "ZA": "South Africa",
    "KR": "South Korea",
    "ES": "Spain",
    "SE": "Sweden",
    # DataForSEO renamed Turkey -> "Turkiye" (the country's 2022 UN rename);
    # "Turkey" now returns 40501 Invalid Field: location_name (found 2026-07-27).
    "TR": "Turkiye",
    "GB": "United Kingdom",
    "US": "United States",
}

# Countries excluded from Google Ads demand collection, each with its reason.
# Google Ads search volume is only meaningful where Google is the dominant
# search engine AND DataForSEO serves the location. Excluded countries are NOT
# offered in the analysis UI (see marketmind-ai country picker) and documented
# in docs/paises-disponiveis.md. `country in UNSUPPORTED_ISO2` checks the keys.
UNSUPPORTED_ISO2: dict[str, str] = {
    "RU": "Russia is unsupported by DataForSEO across all services (sanctions).",
    "BY": "Belarus is unsupported by DataForSEO across all services (sanctions).",
    "CN": "Google is blocked in mainland China (Baidu dominates); Google Ads returns no representative search volume.",
}
