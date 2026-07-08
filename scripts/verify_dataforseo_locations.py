"""One-off, manually-run verification for app/clients/dataforseo_locations.py.

The ISO2_TO_LOCATION_NAME table was written from standard English country
names, NOT confirmed against DataForSEO's own location catalog (that
required a funded/real credential we didn't have at the time). Run this
once real DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD are set in .env, to catch
any name DataForSEO doesn't recognize the way this project guessed it.

This hits the *locations* endpoint only — same behavior in sandbox and
live (it's a static reference list, not billed either way), so there is
no cost concern running this repeatedly.

Usage:
    poetry run python scripts/verify_dataforseo_locations.py
"""

import sys

from dataforseo_client import api_client as dfs_api_provider
from dataforseo_client import configuration as dfs_config
from dataforseo_client.api.keywords_data_api import KeywordsDataApi

from app.clients.dataforseo_locations import ISO2_TO_LOCATION_NAME, UNSUPPORTED_ISO2
from app.core.config import settings


def main() -> int:
    if not settings.dataforseo_login or not settings.dataforseo_password:
        print("DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD not set — nothing to verify against.")
        return 1

    configuration = dfs_config.Configuration(
        username=settings.dataforseo_login,
        password=settings.dataforseo_password,
    )
    with dfs_api_provider.ApiClient(configuration) as api_client:
        api = KeywordsDataApi(api_client)
        response = api.google_trends_locations()

    tasks = response.tasks or []
    if not tasks or not tasks[0].result:
        print("DataForSEO returned no locations — check credentials/account status.")
        return 1

    by_iso2 = {loc.country_iso_code: loc.location_name for loc in tasks[0].result if loc and loc.country_iso_code}

    exit_code = 0
    for iso2, expected_name in ISO2_TO_LOCATION_NAME.items():
        real_name = by_iso2.get(iso2)
        if real_name is None:
            print(f"MISSING  {iso2}: no country-level location found at all in DataForSEO's catalog")
            exit_code = 1
        elif real_name != expected_name:
            print(f"MISMATCH {iso2}: static table says '{expected_name}', DataForSEO calls it '{real_name}'")
            exit_code = 1
        else:
            print(f"OK       {iso2}: '{expected_name}'")

    for iso2 in UNSUPPORTED_ISO2:
        if iso2 in by_iso2:
            print(
                f"NOTE     {iso2}: previously confirmed unsupported, but DataForSEO now lists it as "
                f"'{by_iso2[iso2]}' — consider adding it back to ISO2_TO_LOCATION_NAME"
            )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
