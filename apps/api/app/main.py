"""AI Radar API.

FastAPI-app med base path /api/v1 (Technical Master §11). OpenAPI er
kontraktkilde. API og ingestion/AI-worker deler codebase og domænelag.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.errors import register_exception_handlers
from app.routes import documents, signals, sources

API_PREFIX = "/api/v1"

app = FastAPI(
    title="AI Radar API",
    version="0.2.0",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# CORS begrænses til godkendte origins (Technical Master §12).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

register_exception_handlers(app)
app.include_router(sources.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(signals.router, prefix=API_PREFIX)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness-check til containerhost og CI."""
    return HealthResponse(status="ok", service="ai-radar-api", version=app.version)
