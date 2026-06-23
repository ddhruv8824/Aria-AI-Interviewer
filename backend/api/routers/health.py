"""
api/routers/health.py
──────────────────────
Health-check router.

Endpoints:
    GET  /health          → basic liveness probe
    GET  /health/ready    → readiness probe (checks disk + Gemini key present)
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
import os

from shared.config import API_KEY, MODEL, VOICE_NAME, MEMORY_FILE

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status:  str
    service: str
    model:   str
    voice:   str


class ReadinessResponse(BaseModel):
    status:       str
    api_key_set:  bool
    memory_file:  str
    memory_exists: bool


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """Returns 200 OK as long as the server is running."""
    return HealthResponse(
        status="ok",
        service="Gemini Live Voice Interview Assistant",
        model=MODEL,
        voice=VOICE_NAME,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness_check() -> ReadinessResponse:
    """
    Returns 200 OK when the service is fully ready:
      - API key is configured
      - Memory directory is accessible
    """
    key_set      = bool(API_KEY and len(API_KEY) > 10)
    mem_exists   = os.path.exists(MEMORY_FILE)

    return ReadinessResponse(
        status="ready" if key_set else "degraded",
        api_key_set=key_set,
        memory_file=MEMORY_FILE,
        memory_exists=mem_exists,
    )
