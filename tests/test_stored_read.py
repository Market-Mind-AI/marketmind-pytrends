from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.schemas.requests import StoredSearchVolumeRequest
from app.services.keywords_data_service import KeywordsDataService


def _volume_row(keyword: str, volume: str = "1500") -> SimpleNamespace:
    return SimpleNamespace(
        keyword=keyword,
        location="ES",
        language="en-US",
        search_volume=Decimal(volume),
        competition="HIGH",
        competition_index=80,
        cpc=Decimal("0.45"),
        monthly_searches=[{"year": 2026, "month": 8, "search_volume": 1600}],
        created_at=datetime(2026, 9, 1),
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
        created_at=datetime(2026, 9, 1),
    )


def _service(mock_session: AsyncMock, *, volumes: list | None = None, related: list | None = None):
    service = KeywordsDataService(mock_session)
    service._sv_repo.latest_by_keywords = AsyncMock(return_value=volumes or [])
    service._kr_repo.latest_by_seed = AsyncMock(return_value=related or [])
    return service


async def test_returns_what_is_stored(mock_session: AsyncMock) -> None:
    service = _service(mock_session, volumes=[_volume_row("air fryer")])

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer"])
    )

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

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["Air Fryer"])
    )

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

    response = await service.read_stored_search_volume(
        StoredSearchVolumeRequest(location="ES", keywords=["air fryer"])
    )

    assert response.data.keywords[0].search_volume is None
