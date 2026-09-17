"""AI Radar API.

FastAPI-app med base path /api/v1 (Technical Master §11). OpenAPI er
kontraktkilde. API og ingestion/AI-worker deler codebase og domænelag.
"""

from fastapi import FastAPI
from pydantic import BaseModel

API_PREFIX = "/api/v1"

app = FastAPI(
    title="AI Radar API",
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness-check til containerhost og CI."""
    return HealthResponse(status="ok", service="ai-radar-api", version=app.version)
