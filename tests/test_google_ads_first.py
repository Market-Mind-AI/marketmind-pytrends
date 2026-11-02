"""Google Ads first, DataForSEO only when it does not answer."""

from unittest.mock import MagicMock, patch

import pytest

from app.clients.google_ads_client import _record
from app.core.exceptions import GoogleAdsClientError, GoogleAdsTransientError
from app.services.keywords_data_service import KeywordsDataService

_RESPOSTA = ([{"keyword": "air fryer", "search_volume": 49500}], {"provider": "x"})


def _servico() -> KeywordsDataService:
    servico = KeywordsDataService(MagicMock())
    servico._google_ads = MagicMock()
    servico._client = MagicMock()
    return servico


async def test_google_ads_answers_and_dataforseo_is_not_asked() -> None:
    servico = _servico()
    servico._google_ads.search_volume.return_value = _RESPOSTA
    with patch("app.clients.google_ads_client.configured", return_value=True):
        resposta = await servico._first_answer("search_volume", keywords=["air fryer"], country="ES", language="es")
    assert resposta == _RESPOSTA
    servico._client.search_volume.assert_not_called()


@pytest.mark.parametrize("falha", [GoogleAdsTransientError("503"), GoogleAdsClientError("país"), RuntimeError("?")])
async def test_any_google_ads_failure_is_dataforseos_turn(falha: Exception) -> None:
    """Inclusive a que parece definitiva: quem diz que não há volume é a última
    fonte a responder, não a primeira a falhar."""
    servico = _servico()
    servico._google_ads.keywords_for_keywords.side_effect = falha
    servico._client.keywords_for_keywords.return_value = _RESPOSTA
    with patch("app.clients.google_ads_client.configured", return_value=True):
        resposta = await servico._first_answer(
            "keywords_for_keywords", seed_keywords=["air fryer"], country="TW", language="zh", limit=None
        )
    assert resposta == _RESPOSTA
    servico._client.keywords_for_keywords.assert_called_once()


async def test_without_google_ads_credentials_dataforseo_answers_alone() -> None:
    servico = _servico()
    servico._client.search_volume.return_value = _RESPOSTA
    with patch("app.clients.google_ads_client.configured", return_value=False):
        await servico._first_answer("search_volume", keywords=["air fryer"], country="ES", language="es")
    servico._google_ads.search_volume.assert_not_called()


def test_a_google_ads_keyword_reads_like_a_dataforseo_one() -> None:
    """Mesmo formato que a DataForSEO grava: série do mais novo para o mais
    antigo, mês em número, CPC em moeda (não em micros)."""
    registro = _record(
        "air fryer",
        {
            "avgMonthlySearches": "49500",
            "competition": "HIGH",
            "competitionIndex": "100",
            "averageCpcMicros": "239560",
            "monthlySearchVolumes": [
                {"year": "2025", "month": "OCTOBER", "monthlySearches": "60500"},
                {"year": "2026", "month": "SEPTEMBER", "monthlySearches": "40500"},
            ],
        },
    )
    assert registro == {
        "keyword": "air fryer",
        "search_volume": 49500,
        "competition": "HIGH",
        "competition_index": 100,
        "cpc": 0.23956,
        "monthly_searches": [
            {"year": 2026, "month": 9, "search_volume": 40500},
            {"year": 2025, "month": 10, "search_volume": 60500},
        ],
    }


def test_a_429_waits_as_long_as_google_asks() -> None:
    """Medido em 02/11/2026: o 429 pede 4 a 5 segundos, e o recuo padrão era
    menor — a segunda tentativa batia no mesmo limite e a coleta ia para a
    DataForSEO à toa."""
    from app.clients.google_ads_client import _espera_pedida

    assert _espera_pedida('"message": "Too many requests. Retry in 5 seconds.",') == "5"
    assert _espera_pedida("outro erro qualquer") is None
