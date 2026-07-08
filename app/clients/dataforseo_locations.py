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

Russia is deliberately absent: DataForSEO's own docs confirm Russia and
Belarus are unsupported across all of their services (sanctions), so any
lookup for "RU" must fail loudly (see dataforseo_client.py), not silently
guess a name that doesn't exist in their system.
"""

ISO2_TO_LOCATION_NAME: dict[str, str] = {
    "AR": "Argentina",
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "CL": "Chile",
    "CN": "China",
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
    "TR": "Turkey",
    "GB": "United Kingdom",
    "US": "United States",
}

# Confirmed via DataForSEO docs (2026-07-08), not a mapping gap to fill in.
UNSUPPORTED_ISO2 = frozenset({"RU", "BY"})
