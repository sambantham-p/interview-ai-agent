from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.constants.app import API_V1_PREFIX, SERVICE_NAME
from app.core.db import get_engine
from app.core.db import ping as ping_db
from app.core.exception_handlers import register_exception_handlers
from app.core.gemini_client import get_gemini_client
from app.core.logging import configure_logging
from app.core.request_logging import RequestLoggingMiddleware
from app.routes import health, resume

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await ping_db()
    get_gemini_client()

    yield

    # Client.close() only closes the sync client - the app only ever uses
    # client.aio (see gemini_client.py), so the sync close leaves that
    # connection pool open. Confirmed via Client.close()'s own docstring.
    await get_gemini_client().aio.aclose()
    await get_engine().dispose()


app = FastAPI(
    title=SERVICE_NAME,
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(resume.router, prefix=API_V1_PREFIX)
