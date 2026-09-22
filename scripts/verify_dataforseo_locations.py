"""One-off, manually-run verification for app/clients/dataforseo_locations.py.

The ISO2_TO_LOCATION_NAME table was written from standard English country
names and confirmed against DataForSEO's own catalog on 2026-09-22, once a
funded credential existed: every one of the twenty-four entries matches.

It also answers a second question, which is what it is worth running for now:
which countries DataForSEO covers that this project does not yet analyse.

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

    # SÓ as entradas de país. A lista tem 2.311 localizações e a maioria é
    # subdivisão — província, estado, município. Sem este filtro, o dicionário
    # por ISO2 fica com a ÚLTIMA que passou: "Brazil" virava "State of Acre,
    # Brazil", "United States" virava "Bel Air,California,United States", e as
    # 23 entradas da tabela eram reportadas como divergentes. Todas corretas.
    by_iso2 = {
        loc.country_iso_code: loc.location_name
        for loc in tasks[0].result
        if loc and loc.country_iso_code and getattr(loc, "location_type", None) == "Country"
    }

    print(f"DataForSEO lista {len(by_iso2)} países. A tabela deste projeto tem {len(ISO2_TO_LOCATION_NAME)}.\n")

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
            # Não é erro de dado. Estar no catálogo não é o mesmo que o dado
            # significar alguma coisa: a China é listada, e o Google é bloqueado
            # lá, então o volume de busca não representa aquele mercado. A
            # exclusão é substantiva e a nota existe para que ela seja revista de
            # olho aberto, não para acusar divergência.
            print(
                f"NOTE     {iso2}: DataForSEO lists it as '{by_iso2[iso2]}'. Excluded here for a reason "
                "that is not coverage — see the docstring in app/clients/dataforseo_locations.py."
            )

    novos = sorted(set(by_iso2) - set(ISO2_TO_LOCATION_NAME) - set(UNSUPPORTED_ISO2))
    if novos:
        print(f"\n{len(novos)} países que a DataForSEO cobre e este projeto ainda não analisa.")
        print("Acrescentar um exige mais que este nome: o idioma em que se busca ali, que é")
        print("curado por país e decide de que produto a análise fala.")
        print("  " + " ".join(novos))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
