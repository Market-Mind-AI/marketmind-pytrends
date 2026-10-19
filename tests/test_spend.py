"""What a request spent at DataForSEO reaches the caller, not only the log."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.clients.dataforseo_client import DataForSEOClient
from app.core import spend
from app.main import app
from tests.test_dataforseo_client import _install_api, _response_with_results, _result_item
from tests.test_endpoints import _mock_session, _override_session, _sv_records


def test_the_tally_adds_what_each_task_was_billed() -> None:
    with spend.collect() as spent:
        spend.add(0.05)
        spend.add(0.0075)
        spend.add(None)  # a task that carried no figure

    assert spent.usd == 0.0575
    assert spent.calls == 3
    assert spent.calls_without_cost == 1


def test_outside_a_request_nothing_is_counted_and_nothing_breaks() -> None:
    spend.add(0.05)

    assert spend.current() is None


def test_the_headers_say_cost_and_calls_and_what_went_unpriced() -> None:
    assert spend.headers(spend.Spend()) == {}
    assert spend.headers(spend.Spend(usd=0.0575, calls=3, calls_without_cost=1)) == {
        "X-DataForSEO-Cost-USD": "0.057500",
        "X-DataForSEO-Calls": "3",
        "X-DataForSEO-Calls-Without-Cost": "1",
    }


@patch("app.clients.dataforseo_client.KeywordsDataApi")
@patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
def test_an_answered_task_is_added_to_the_open_tally(
    mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
) -> None:
    response = _response_with_results([_result_item()])
    response.tasks[0].cost = 0.05
    mock_api = MagicMock()
    mock_api.google_ads_search_volume_live.return_value = response
    _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

    with spend.collect() as spent:
        DataForSEOClient().search_volume(["air fryer"], "ES", "en-US")

    assert (spent.usd, spent.calls, spent.calls_without_cost) == (0.05, 1, 0)


@patch("app.clients.dataforseo_client.KeywordsDataApi")
@patch("app.clients.dataforseo_client.dfs_api_provider.ApiClient")
def test_a_failed_task_is_still_counted_because_it_is_still_billed(
    mock_api_client_cls: MagicMock, mock_keywords_api_cls: MagicMock
) -> None:
    import pytest

    from app.core.exceptions import DataForSEOClientError

    response = _response_with_results([], status_code=40000)
    response.tasks[0].cost = 0.05
    mock_api = MagicMock()
    mock_api.google_ads_search_volume_live.return_value = response
    _install_api(mock_api_client_cls, mock_keywords_api_cls, mock_api)

    with spend.collect() as spent, pytest.raises(DataForSEOClientError):
        DataForSEOClient().search_volume(["air fryer"], "ES", "en-US")

    assert spent.usd == 0.05


def test_the_response_carries_the_spend_in_its_headers() -> None:
    """The client runs in a worker thread (asyncio.to_thread); the context is
    copied into it, so the thread adds to the request's own tally."""

    def _collect(*args: object, **kwargs: object):  # noqa: ANN202
        spend.add(0.05)
        spend.add(0.0075)
        return _sv_records(), {"provider": "dataforseo_google_ads"}

    _override_session(_mock_session())
    try:
        with patch("app.clients.dataforseo_client.DataForSEOClient.search_volume", side_effect=_collect):
            response = TestClient(app).post(
                "/search-volume", json={"location": "ES", "language": "en-US", "keywords": ["air fryer"]}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["X-DataForSEO-Cost-USD"] == "0.057500"
    assert response.headers["X-DataForSEO-Calls"] == "2"
    assert "X-DataForSEO-Calls-Without-Cost" not in response.headers


def test_a_request_that_spent_nothing_says_nothing() -> None:
    response = TestClient(app).get("/health")

    assert "X-DataForSEO-Cost-USD" not in response.headers
