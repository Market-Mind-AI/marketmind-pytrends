import pytest
from pydantic import ValidationError

from app.schemas.requests import SuggestionRequest, TrendRequest


class TestTrendRequest:
    def test_valid_request(self) -> None:
        req = TrendRequest(keyword="air fryer", country="ES")
        assert req.keyword == "air fryer"
        assert req.country == "ES"
        assert req.timeframe == "today 12-m"
        assert req.language == "en-US"

    def test_keyword_min_length(self) -> None:
        with pytest.raises(ValidationError):
            TrendRequest(keyword="a", country="ES")

    def test_country_must_be_iso2(self) -> None:
        with pytest.raises(ValidationError):
            TrendRequest(keyword="air fryer", country="ESP")

    def test_country_must_be_uppercase(self) -> None:
        with pytest.raises(ValidationError):
            TrendRequest(keyword="air fryer", country="es")

    def test_custom_timeframe(self) -> None:
        req = TrendRequest(keyword="air fryer", country="US", timeframe="today 3-m")
        assert req.timeframe == "today 3-m"

    def test_custom_language(self) -> None:
        req = TrendRequest(keyword="air fryer", country="BR", language="pt-BR")
        assert req.language == "pt-BR"


class TestSuggestionRequest:
    def test_valid_request(self) -> None:
        req = SuggestionRequest(keyword="air fryer")
        assert req.keyword == "air fryer"
        assert req.language == "en-US"

    def test_keyword_min_length(self) -> None:
        with pytest.raises(ValidationError):
            SuggestionRequest(keyword="a")
