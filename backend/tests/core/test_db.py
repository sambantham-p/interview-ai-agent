import pytest
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.db import get_db, get_engine, get_session_factory, to_asyncpg_url


def test_to_asyncpg_url_rewrites_postgresql_scheme() -> None:
    assert (
        to_asyncpg_url("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
    )


def test_to_asyncpg_url_leaves_already_asyncpg_scheme_untouched() -> None:
    url = "postgresql+asyncpg://u:p@host/db"
    assert to_asyncpg_url(url) == url


def test_to_asyncpg_url_strips_libpq_only_query_params() -> None:
    # Neon's connection string includes sslmode/channel_binding, which are
    # libpq/psycopg query params asyncpg.connect() doesn't accept as
    # keyword arguments - SQLAlchemy's asyncpg dialect passes query
    # params straight through as kwargs, so these must be stripped (SSL
    # is enabled separately via connect_args in get_engine()).
    url = "postgresql://u:p@host/db?sslmode=require&channel_binding=require"
    assert to_asyncpg_url(url) == "postgresql+asyncpg://u:p@host/db"


def test_get_engine_builds_asyncpg_url_and_is_cached(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.db.get_settings",
        return_value=Settings(database_url="postgresql://u:p@host/db"),
    )
    get_engine.cache_clear()

    engine = get_engine()

    assert (
        engine.url.render_as_string(hide_password=False)
        == "postgresql+asyncpg://u:p@host/db"
    )
    assert engine is get_engine()

    get_engine.cache_clear()


def test_get_session_factory_is_bound_to_get_engine(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.db.get_settings",
        return_value=Settings(database_url="postgresql://u:p@host/db"),
    )
    get_engine.cache_clear()

    session_factory = get_session_factory()

    assert session_factory.kw["bind"] is get_engine()

    get_engine.cache_clear()


async def test_get_db_yields_session_and_closes_it(mocker: MockerFixture) -> None:
    fake_session = mocker.AsyncMock()
    fake_session_cm = mocker.MagicMock()
    fake_session_cm.__aenter__ = mocker.AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = mocker.AsyncMock(return_value=False)
    fake_session_factory = mocker.MagicMock(return_value=fake_session_cm)
    mocker.patch("app.core.db.get_session_factory", return_value=fake_session_factory)

    agen = get_db()
    session = await agen.__anext__()
    assert session is fake_session

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    fake_session_cm.__aexit__.assert_awaited_once()
