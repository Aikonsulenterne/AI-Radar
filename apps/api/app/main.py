"""AI Radar API.

FastAPI-app med base path /api/v1 (Technical Master §11). OpenAPI er
kontraktkilde. API og ingestion/AI-worker deler codebase og domænelag.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.context import request_id_var
from app.errors import register_exception_handlers
from app.routes import audit, catalog, documents, opportunities, signals, sources

API_PREFIX = "/api/v1"

logger = logging.getLogger("ai_radar.http")

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


@app.middleware("http")
async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Correlation id + operational log pr. request (Technical Master §18).

    Logger aldrig tokens, headers eller request bodies — kun metode, sti,
    status og varighed.
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    token = request_id_var.set(request_id)
    started = time.monotonic()
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "http method=%s path=%s status=%d duration_ms=%d request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


register_exception_handlers(app)
app.include_router(sources.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(signals.router, prefix=API_PREFIX)
app.include_router(catalog.router, prefix=API_PREFIX)
app.include_router(opportunities.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness-check til containerhost og CI."""
    return HealthResponse(status="ok", service="ai-radar-api", version=app.version)
