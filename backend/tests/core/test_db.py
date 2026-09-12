import pytest
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.db import get_db, get_engine, get_session_factory, ping, to_asyncpg_url


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


def test_get_engine_enables_pre_ping_and_recycle(mocker: MockerFixture) -> None:
    # Neon can drop a pooled connection server-side (compute suspend on
    # the free tier, or an idle timeout) independently of anything this
    # app does - without pre_ping, the next query on that stale
    # connection fails with asyncpg's InterfaceError: connection is
    # closed, surfaced all the way up to the caller (confirmed live on
    # POST /resume/upload). pre_ping catches this at checkout instead of
    # letting it reach a query; pool_recycle proactively retires old
    # connections as a second line of defense.
    mocker.patch(
        "app.core.db.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )
    fake_create_engine = mocker.patch("app.core.db.create_async_engine")
    get_engine.cache_clear()

    get_engine()

    assert fake_create_engine.call_args.kwargs["pool_pre_ping"] is True
    assert fake_create_engine.call_args.kwargs["pool_recycle"] == 300

    get_engine.cache_clear()


def test_get_engine_disables_asyncpg_statement_cache(mocker: MockerFixture) -> None:
    # DATABASE_URL points at Neon's "-pooler" (PgBouncer transaction-mode)
    # endpoint - the right choice for a long-running server, but
    # transaction pooling multiplexes client transactions across
    # different backend connections, which breaks asyncpg's default
    # server-side prepared statement cache (DuplicatePreparedStatementError
    # / "prepared statement does not exist" under concurrent load - a
    # documented asyncpg+PgBouncer incompatibility). statement_cache_size=0
    # turns that caching off.
    mocker.patch(
        "app.core.db.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )
    fake_create_engine = mocker.patch("app.core.db.create_async_engine")
    get_engine.cache_clear()

    get_engine()

    assert (
        fake_create_engine.call_args.kwargs["connect_args"]["statement_cache_size"] == 0
    )

    get_engine.cache_clear()


def test_get_engine_builds_asyncpg_url_and_is_cached(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.db.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
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
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )
    get_engine.cache_clear()

    session_factory = get_session_factory()

    assert session_factory.kw["bind"] is get_engine()
    # expire_on_commit=False: ORM objects stay usable after commit, e.g.
    # returning a just-created row in an API response without a refresh.
    assert session_factory.kw["expire_on_commit"] is False

    get_engine.cache_clear()


async def test_ping_runs_select_1_against_a_real_connection(
    mocker: MockerFixture,
) -> None:
    fake_conn = mocker.AsyncMock()
    fake_conn_cm = mocker.MagicMock()
    fake_conn_cm.__aenter__ = mocker.AsyncMock(return_value=fake_conn)
    fake_conn_cm.__aexit__ = mocker.AsyncMock(return_value=False)
    fake_engine = mocker.MagicMock()
    fake_engine.connect = mocker.MagicMock(return_value=fake_conn_cm)
    mocker.patch("app.core.db.get_engine", return_value=fake_engine)

    await ping()

    fake_conn.execute.assert_awaited_once()
    (query,), _ = fake_conn.execute.call_args
    assert str(query) == "SELECT 1"


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
