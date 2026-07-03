import pandas as pd

from app.utils.normalization import (
    normalize_interest_by_region,
    normalize_interest_over_time,
    normalize_related_queries,
    normalize_related_topics,
    normalize_suggestions,
)


class TestNormalizeInterestOverTime:
    def test_basic_normalization(self) -> None:
        index = pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"])
        df = pd.DataFrame(
            {"air fryer": [50, 75, 100], "isPartial": [False, False, True]},
            index=index,
        )
        result = normalize_interest_over_time(df, "air fryer")
        assert len(result) == 3
        assert result[0]["date"] == "2025-01-01"
        assert result[0]["value"] == 50
        assert result[0]["is_partial"] is False
        assert result[2]["is_partial"] is True

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        result = normalize_interest_over_time(df, "air fryer")
        assert result == []

    def test_nan_values_become_zero(self) -> None:
        index = pd.to_datetime(["2025-01-01"])
        df = pd.DataFrame({"air fryer": [float("nan")], "isPartial": [False]}, index=index)
        result = normalize_interest_over_time(df, "air fryer")
        assert result[0]["value"] == 0

    def test_dates_are_iso_format(self) -> None:
        index = pd.to_datetime(["2025-06-15"])
        df = pd.DataFrame({"test": [42], "isPartial": [False]}, index=index)
        result = normalize_interest_over_time(df, "test")
        assert result[0]["date"] == "2025-06-15"


class TestNormalizeInterestByRegion:
    def test_basic_normalization(self) -> None:
        df = pd.DataFrame(
            {"air fryer": [82, 65, 40]},
            index=["Madrid", "Barcelona", "Seville"],
        )
        result = normalize_interest_by_region(df, "air fryer")
        assert len(result) == 3
        assert result[0]["region"] == "Madrid"
        assert result[0]["value"] == 82

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        result = normalize_interest_by_region(df, "air fryer")
        assert result == []


class TestNormalizeRelatedQueries:
    def test_basic_normalization(self) -> None:
        data = {
            "air fryer": {
                "top": pd.DataFrame({"query": ["best air fryer"], "value": [100]}),
                "rising": pd.DataFrame({"query": ["dual basket"], "value": [350]}),
            }
        }
        result = normalize_related_queries(data, "air fryer")
        assert len(result["top"]) == 1
        assert result["top"][0]["query"] == "best air fryer"
        assert result["top"][0]["value"] == 100
        assert len(result["rising"]) == 1
        assert result["rising"][0]["query"] == "dual basket"

    def test_empty_results(self) -> None:
        data = {
            "air fryer": {
                "top": pd.DataFrame(),
                "rising": None,
            }
        }
        result = normalize_related_queries(data, "air fryer")
        assert result["top"] == []
        assert result["rising"] == []


class TestNormalizeRelatedTopics:
    def test_basic_normalization(self) -> None:
        data = {
            "air fryer": {
                "top": pd.DataFrame(
                    {
                        "topic_title": ["Air fryer"],
                        "topic_mid": ["/m/abc"],
                        "value": [100],
                    }
                ),
                "rising": pd.DataFrame(
                    {
                        "topic_title": ["Healthy cooking"],
                        "topic_mid": ["/m/xyz"],
                        "value": [180],
                    }
                ),
            }
        }
        result = normalize_related_topics(data, "air fryer")
        assert len(result["top"]) == 1
        assert result["top"][0]["topic"] == "Air fryer"
        assert result["top"][0]["mid"] == "/m/abc"

    def test_empty_results(self) -> None:
        data = {"air fryer": {"top": None, "rising": pd.DataFrame()}}
        result = normalize_related_topics(data, "air fryer")
        assert result["top"] == []
        assert result["rising"] == []


class TestNormalizeSuggestions:
    def test_basic_normalization(self) -> None:
        data = [
            {"title": "Air fryer", "type": "Topic", "mid": "/m/abc"},
            {"title": "Air fryer recipes", "type": "Search term", "mid": None},
        ]
        result = normalize_suggestions(data)
        assert len(result) == 2
        assert result[0]["title"] == "Air fryer"
        assert result[0]["type"] == "Topic"
        assert result[0]["mid"] == "/m/abc"
        assert result[1]["mid"] is None

    def test_empty_list(self) -> None:
        result = normalize_suggestions([])
        assert result == []
