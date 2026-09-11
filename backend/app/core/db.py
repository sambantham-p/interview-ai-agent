from collections.abc import AsyncGenerator
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def to_asyncpg_url(database_url: str) -> str:
    """Convert a libpq-style Postgres URL (as Neon provides it) into one
    SQLAlchemy's asyncpg dialect accepts. asyncpg's Python API takes an
    `ssl` keyword argument, not the `sslmode`/`channel_binding` query
    params libpq uses - passing those through as query params makes
    asyncpg.connect() raise `TypeError: unexpected keyword argument
    'sslmode'`. TLS is enabled explicitly via connect_args instead, see
    get_engine().
    """
    scheme, netloc, path, _query, fragment = urlsplit(database_url)
    if scheme == "postgresql":
        scheme = "postgresql+asyncpg"
    return urlunsplit((scheme, netloc, path, "", fragment))


@lru_cache
def get_engine() -> AsyncEngine:
    # Cached + built lazily (not at import time) so importing this module
    # never requires DATABASE_URL to be set - only actually using the
    # engine does.
    return create_async_engine(
        to_asyncpg_url(get_settings().database_url), connect_args={"ssl": True}
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def ping() -> None:
    """Verify Postgres is actually reachable - call at app startup so a
    bad DATABASE_URL or unreachable DB fails fast, not on the first request.
    """
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
