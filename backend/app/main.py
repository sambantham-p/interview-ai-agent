from fastapi import FastAPI

from app.constants.app import API_V1_PREFIX, SERVICE_NAME
from app.core.exception_handlers import register_exception_handlers
from app.routes import health

app = FastAPI(
    title=SERVICE_NAME,
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

register_exception_handlers(app)

app.include_router(health.router, prefix=API_V1_PREFIX)
