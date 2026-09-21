from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with patch("app.api.routes.health.get_session") as mock_get_session:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        async def session_gen():  # type: ignore[no-untyped-def]
            yield mock_session

        mock_get_session.return_value = session_gen()

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == "marketmind-pytrends"


def test_healthz_answers_without_touching_the_database() -> None:
    """What a liveness probe asks: can THIS process still answer. It must not
    depend on Postgres — a probe that does restarts the pod because the database
    is slow, which fixes nothing and throws away whatever was in flight.

    No database fixture here, deliberately: if this endpoint ever starts needing
    one, this test fails.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
