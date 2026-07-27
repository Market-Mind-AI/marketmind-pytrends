"""Static ISO2 -> DataForSEO `location_name` mapping for the Google Trends
Explore endpoint, scoped to marketmind-core's ~27-country reference basket
(same "canonical table built once, no LLM" philosophy already applied to
country-code de-para elsewhere in the project — see marketmind-core memory
marketmind_known_gaps item 6).

English short names below are NOT yet confirmed against DataForSEO's own
`GET /v3/keywords_data/google_trends/locations` list (that call needs a
real, funded credential we didn't have while writing this). Run
scripts/verify_dataforseo_locations.py once real credentials are set to
confirm or correct every entry — do not trust this table blindly for a new
country before that script has checked it.

Russia/Belarus are deliberately absent: DataForSEO's own docs confirm they are
unsupported across all of their services (sanctions), so any lookup must fail
loudly (see dataforseo_client.py), not silently guess a name. China is likewise
excluded (in UNSUPPORTED_ISO2, not here): Google is blocked in mainland China so
Google Ads returns no representative search volume. See docs/paises-disponiveis.md.
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
