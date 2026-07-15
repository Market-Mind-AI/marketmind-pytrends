import pytest
from pydantic import ValidationError

from app.schemas.requests import KeywordsForKeywordsRequest, SearchVolumeRequest


class TestSearchVolumeRequest:
    def test_valid_request(self) -> None:
        req = SearchVolumeRequest(location="ES", keywords=["air fryer", "robot vacuum"])
        assert req.location == "ES"
        assert req.language == "en-US"
        assert req.keywords == ["air fryer", "robot vacuum"]

    def test_location_must_be_iso2(self) -> None:
        with pytest.raises(ValidationError):
            SearchVolumeRequest(location="ESP", keywords=["air fryer"])

    def test_location_must_be_uppercase(self) -> None:
        with pytest.raises(ValidationError):
            SearchVolumeRequest(location="es", keywords=["air fryer"])

    def test_keywords_required_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            SearchVolumeRequest(location="ES", keywords=[])

    def test_keywords_capped_at_1000(self) -> None:
        with pytest.raises(ValidationError):
            SearchVolumeRequest(location="ES", keywords=[f"kw{i}" for i in range(1001)])

    def test_custom_language(self) -> None:
        req = SearchVolumeRequest(location="BR", language="pt-BR", keywords=["air fryer"])
        assert req.language == "pt-BR"


class TestKeywordsForKeywordsRequest:
    def test_valid_request(self) -> None:
        req = KeywordsForKeywordsRequest(location="ES", seed_keywords=["air fryer"], limit=100)
        assert req.location == "ES"
        assert req.seed_keywords == ["air fryer"]
        assert req.limit == 100

    def test_limit_optional(self) -> None:
        req = KeywordsForKeywordsRequest(location="ES", seed_keywords=["air fryer"])
        assert req.limit is None

    def test_seeds_capped_at_20(self) -> None:
        with pytest.raises(ValidationError):
            KeywordsForKeywordsRequest(location="ES", seed_keywords=[f"kw{i}" for i in range(21)])

    def test_seeds_required_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            KeywordsForKeywordsRequest(location="ES", seed_keywords=[])
