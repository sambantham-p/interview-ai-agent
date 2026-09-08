from fastapi import FastAPI

from app.routes import health

app = FastAPI(title="interview-ai-agent")

app.include_router(health.router)
