from fastapi import FastAPI

from app.constants import API_V1_PREFIX
from app.routes import health

app = FastAPI(
    title="interview-ai-agent",
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

app.include_router(health.router, prefix=API_V1_PREFIX)
