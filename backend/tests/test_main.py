from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.main import app


def test_lifespan_pings_db_and_prepares_gemini_client_on_startup(
    mocker: MockerFixture,
) -> None:
    fake_ping_db = mocker.patch("app.main.ping_db", new=mocker.AsyncMock())
    fake_gemini_client = mocker.MagicMock()
    fake_gemini_client.aio.aclose = mocker.AsyncMock()
    fake_get_gemini_client = mocker.patch(
        "app.main.get_gemini_client", return_value=fake_gemini_client
    )
    fake_engine = mocker.MagicMock()
    fake_engine.dispose = mocker.AsyncMock()
    mocker.patch("app.main.get_engine", return_value=fake_engine)

    with TestClient(app, headers={"X-Request-ID": "sam-interview-ai-agent"}):
        pass

    fake_ping_db.assert_awaited_once()
    fake_get_gemini_client.assert_called()


def test_lifespan_startup_survives_db_and_gemini_failures(
    mocker: MockerFixture,
) -> None:
    # /health is a liveness check with no dependency on DB/Gemini (see
    # app/routes/health.py) - startup must not raise when either
    # dependency is down, or the app never binds its port and /health
    # becomes unreachable too.
    mocker.patch("app.main.ping_db", side_effect=RuntimeError("db unreachable"))
    mocker.patch(
        "app.main.get_gemini_client", side_effect=RuntimeError("bad gemini config")
    )
    fake_engine = mocker.MagicMock()
    fake_engine.dispose = mocker.AsyncMock()
    mocker.patch("app.main.get_engine", return_value=fake_engine)

    with TestClient(app, headers={"X-Request-ID": "sam-interview-ai-agent"}) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_lifespan_closes_gemini_client_and_disposes_db_engine_on_shutdown(
    mocker: MockerFixture,
) -> None:
    mocker.patch("app.main.ping_db", new=mocker.AsyncMock())
    fake_gemini_client = mocker.MagicMock()
    fake_gemini_client.aio.aclose = mocker.AsyncMock()
    fake_engine = mocker.MagicMock()
    fake_engine.dispose = mocker.AsyncMock()

    mocker.patch("app.main.get_gemini_client", return_value=fake_gemini_client)
    mocker.patch("app.main.get_engine", return_value=fake_engine)

    with TestClient(app, headers={"X-Request-ID": "sam-interview-ai-agent"}):
        pass

    # Client.close() (sync) explicitly does NOT close the async client per
    # its own docstring - the app only ever uses .aio, so shutdown must
    # close that instead, or the connection pool leaks on every restart.
    fake_gemini_client.aio.aclose.assert_awaited_once()
    fake_gemini_client.close.assert_not_called()
    fake_engine.dispose.assert_awaited_once()
