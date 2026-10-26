from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.schemas.requests import StoredSearchVolumeRequest
from app.services.keywords_data_service import KeywordsDataService


# `created_at` COM fuso porque é assim que a coluna volta: as duas tabelas são
# `timestamp with time zone`. Um fixture ingênuo passa a comparar com um corte
# ingênuo e o teste fica verde enquanto a produção levanta `TypeError: can't
# compare offset-naive and offset-aware datetimes` -- foi exatamente assim que o
# `/freshness` do OECD e o do World Bank passaram semanas quebrados com dez
# testes verdes cada.
def _agora_menos(dias: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=dias)


def _volume_row(keyword: str, volume: str = "1500", *, dias: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        keyword=keyword,
        location="ES",
        language="en-US",
        search_volume=Decimal(volume),
        competition="HIGH",
        competition_index=80,
        cpc=Decimal("0.45"),
        monthly_searches=[{"year": 2026, "month": 8, "search_volume": 1600}],
        created_at=_agora_menos(dias),
    )


def _related_row(keyword: str, seed: str = "air fryer") -> SimpleNamespace:
    return SimpleNamespace(
        seed_keyword=seed,
        keyword=keyword,
        location="ES",
        language="en-US",
        search_volume=Decimal("900"),
        competition_index=50,
        cpc=Decimal("0.30"),
        monthly_searches=[],
        created_at=_agora_menos(0),
    )


def _service(
    mock_session: AsyncMock,
    *,
    volumes: list | None = None,
    related: list | None = None,
    checks: dict | None = None,
):
    """Sem `checks`, cada linha guardada conta como verificada na data em que
    foi coletada -- é o que a migração 008 grava para o que já existia."""
    service = KeywordsDataService(mock_session)
    service._sv_repo.latest_by_keywords = AsyncMock(return_value=volumes or [])
    service._kr_repo.latest_by_seed = AsyncMock(return_value=related or [])
    if checks is None:
        checks = {row.keyword.lower(): row.created_at for row in volumes or []}
    service._check_repo.last_checks = AsyncMock(return_value=checks)
    return service


async def test_returns_what_is_stored(mock_session: AsyncMock) -> None:
    service = _service(mock_session, volumes=[_volume_row("air fryer")])

    response = await service.read_stored_search_volume(StoredSearchVolumeRequest(location="ES", keywords=["air fryer"]))

    assert [k.keyword for k in response.data.keywords] == ["air fryer"]
    assert response.data.keywords[0].search_volume == 1500.0
    assert response.data.missing == []


async def test_missing_lists_what_still_needs_collecting(mock_session: AsyncMock) -> None:
    service = _service(mock_session, volumes=[_volume_row("air fryer")])

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer", "freidora de aire"])
    )

    assert response.data.missing == ["freidora de aire"]


async def test_a_capitalised_term_is_not_reported_missing(mock_session: AsyncMock) -> None:
    """DataForSEO stores keywords lowercased. Matching case-sensitively would
    make a curated term with capitals look missing forever and re-download it
    every run, and every one of those calls is billed."""
    service = _service(mock_session, volumes=[_volume_row("air fryer")])

    response = await service.read_stored_search_volume(StoredSearchVolumeRequest(location="ES", keywords=["Air Fryer"]))

    assert response.data.missing == []


async def test_missing_preserves_the_caller_s_spelling(mock_session: AsyncMock) -> None:
    """The comparison is lowercased, the answer is not: what comes back in
    `missing` is what the caller has to send to a collection."""
    service = _service(mock_session)

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["Freidora De Aire"])
    )

    assert response.data.missing == ["Freidora De Aire"]


async def test_nothing_stored_means_everything_is_missing(mock_session: AsyncMock) -> None:
    service = _service(mock_session)

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="PT", keywords=["air fryer", "fritadeira"])
    )

    assert response.data.keywords == []
    assert response.data.missing == ["air fryer", "fritadeira"]


async def test_related_returns_one_row_per_keyword(mock_session: AsyncMock) -> None:
    service = _service(mock_session, related=[_related_row("airfryer barata"), _related_row("air fryer 5l")])

    response = await service.read_stored_related(location="ES", seed_keyword="air fryer")

    assert [k.keyword for k in response.data.keywords] == ["airfryer barata", "air fryer 5l"]
    assert response.data.seed_keyword == "air fryer"


async def test_related_with_nothing_stored_is_an_empty_list(mock_session: AsyncMock) -> None:
    service = _service(mock_session)

    response = await service.read_stored_related(location="ES", seed_keyword="never expanded")

    assert response.data.keywords == []


async def test_a_null_volume_stays_null_rather_than_becoming_zero(mock_session: AsyncMock) -> None:
    """Zero searches and "we have no figure" are different facts, and the
    difference decides whether a market looks dead or unmeasured."""
    row = _volume_row("air fryer")
    row.search_volume = None
    service = _service(mock_session, volumes=[row])

    response = await service.read_stored_search_volume(StoredSearchVolumeRequest(location="ES", keywords=["air fryer"]))

    assert response.data.keywords[0].search_volume is None


async def test_a_term_collected_long_ago_counts_as_missing(mock_session: AsyncMock) -> None:
    """A demanda é o único indicador que muda de mês para mês, e era o único que
    nunca se renovava. `missing` significava "nunca coletado", e como quem chama
    só monta coleta para o que está em `missing`, um volume baixado em janeiro
    era lido como verdade em setembro — para sempre, sem nada acusar."""
    service = _service(mock_session, volumes=[_volume_row("air fryer", dias=45)])

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer"], stale_after_days=30)
    )

    assert response.data.missing == ["air fryer"]


async def test_a_recent_term_is_not_recollected(mock_session: AsyncMock) -> None:
    """O outro lado, e o que custa dinheiro: dentro do prazo não se pergunta à
    DataForSEO, que cobra por chamada."""
    service = _service(mock_session, volumes=[_volume_row("air fryer", dias=3)])

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer"], stale_after_days=30)
    )

    assert response.data.missing == []


async def test_a_stale_term_still_reports_its_last_known_value(mock_session: AsyncMock) -> None:
    """Vencido entra em `missing` mas NÃO some de `keywords`: quem chama ainda
    pode usar o último valor conhecido enquanto a coleta não termina. O que
    muda é o pedido de coleta, não o que se sabe."""
    service = _service(mock_session, volumes=[_volume_row("air fryer", dias=45)])

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer"], stale_after_days=30)
    )

    assert [k.keyword for k in response.data.keywords] == ["air fryer"]
    assert response.data.keywords[0].search_volume == 1500.0


async def test_without_a_deadline_nothing_expires(mock_session: AsyncMock) -> None:
    """O comportamento antigo continua disponível e é o padrão: sem
    `stale_after_days`, idade nenhuma torna um termo coletável de novo. Quem
    chama decide a política; este serviço só responde a pergunta."""
    service = _service(mock_session, volumes=[_volume_row("air fryer", dias=900)])

    response = await service.read_stored_search_volume(StoredSearchVolumeRequest(location="ES", keywords=["air fryer"]))

    assert response.data.missing == []


async def test_a_term_google_ads_answered_without_a_row_is_not_missing(mock_session: AsyncMock) -> None:
    """O Google Ads não tem volume para todo termo, e a resposta vem sem linha
    para ele. Lido das linhas, esse termo ficava em `missing` para sempre e era
    cobrado a cada análise. A resposta conta como verificação."""
    service = _service(mock_session, volumes=[], checks={"freidora de aire": _agora_menos(3)})

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["Freidora de Aire"], stale_after_days=30)
    )

    assert response.data.missing == []
    assert response.data.keywords == []


async def test_an_old_answer_without_a_row_expires_like_any_other(mock_session: AsyncMock) -> None:
    service = _service(mock_session, volumes=[], checks={"freidora de aire": _agora_menos(45)})

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["freidora de aire"], stale_after_days=30)
    )

    assert response.data.missing == ["freidora de aire"]


async def test_a_collection_records_a_check_for_every_keyword_asked(mock_session: AsyncMock) -> None:
    """Inclusive o que voltou sem linha. Uma coleta que falhou não registra."""
    from app.schemas.requests import SearchVolumeRequest

    service = KeywordsDataService(mock_session)
    service._client.search_volume = lambda **kwargs: ([{"keyword": "air fryer"}], {})  # type: ignore[method-assign]
    service._sv_repo.bulk_create = AsyncMock()
    service._raw_response_repo.create = AsyncMock()
    service._check_repo.record = AsyncMock()

    await service.collect_search_volume(SearchVolumeRequest(location="ES", keywords=["air fryer", "sin volumen"]))

    assert service._check_repo.record.await_args.kwargs["keywords"] == ["air fryer", "sin volumen"]


async def test_a_failed_collection_records_no_check(mock_session: AsyncMock) -> None:
    import pytest

    from app.core.exceptions import DataForSEOTransientError
    from app.schemas.requests import SearchVolumeRequest

    def _down(**kwargs: object) -> None:
        raise DataForSEOTransientError("down")

    service = KeywordsDataService(mock_session)
    service._client.search_volume = _down  # type: ignore[method-assign]
    service._check_repo.record = AsyncMock()

    with pytest.raises(DataForSEOTransientError):
        await service.collect_search_volume(SearchVolumeRequest(location="ES", keywords=["air fryer"]))

    service._check_repo.record.assert_not_awaited()
