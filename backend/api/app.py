"""
api/app.py
───────────
FastAPI application factory.

Creates and configures the FastAPI app with:
  • CORS middleware (permissive for local dev — tighten for production)
  • GZip compression for large payloads
  • All service routers mounted under /api/v1
  • WebSocket session endpoint at /ws/session
  • Rich OpenAPI metadata (title, description, tags)

The Next.js frontend (frontend/) runs separately and talks to this API.
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.middleware.gzip import GZipMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

from api.routers import health, resume, memory, judge, session, code_run, job_description, platform
from shared.logging_config import configure_logging, get_logger

configure_logging(level="DEBUG")
_app_log = get_logger("app")

# ──────────────────────────────────────────────
# OpenAPI metadata
# ──────────────────────────────────────────────
_DESCRIPTION = """
## Gemini Live Voice Interview Assistant — REST + WebSocket API

This API exposes each internal service of the voice interview assistant
as independently consumable HTTP endpoints, plus a real-time WebSocket
session for browser-based voice interviews.

### Services

| Tag | Description |
|-----|-------------|
| **Health** | Liveness / readiness probes |
| **Resume** | Upload a PDF/DOCX resume → structured JSON or system-prompt context |
| **Memory** | Read, inspect, or clear persisted conversation memory |
| **Judge** | Submit an interview transcript → LLM-as-Judge scorecard |
| **Session** | Real-time WebSocket bridge: browser audio ↔ Gemini Live |

### Real-time WebSocket

Connect to `ws://<host>/ws/session` to start a voice interview session.
The Next.js frontend uses this automatically.

### Authentication
Set `API_KEY` in `ai/shared/config.py` to configure your Gemini credentials.
"""

_TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Liveness and readiness probes for the API server.",
    },
    {
        "name": "Resume",
        "description": (
            "Parse PDF/DOCX resumes into structured data or generate a "
            "Gemini system-prompt context block."
        ),
    },
    {
        "name": "Platform",
        "description": (
            "Homepage data: company tracks, community questions, experience blogs, "
            "and practice session registration."
        ),
    },
    {
        "name": "Memory",
        "description": (
            "Read and manage the LangGraph-powered persistent conversation memory. "
            "Memory survives across voice sessions."
        ),
    },
    {
        "name": "Judge",
        "description": (
            "LLM-as-Judge interview evaluation. Submit a transcript and receive "
            "a multi-dimensional scorecard scored by Gemini."
        ),
    },
    {
        "name": "Code",
        "description": (
            "LeetCode-style code execution via self-hosted Judge0. "
            "POST /code/run with source code and test cases."
        ),
    },
    {
        "name": "Session",
        "description": (
            "Real-time WebSocket endpoint. Connect to `/ws/session` for a full "
            "bidirectional audio interview session (browser mic → Gemini → browser speaker)."
        ),
    },
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    _app_log.info("creating FastAPI application")
    app = FastAPI(
        title="Voice Interview Assistant API",
        description=_DESCRIPTION,
        version="1.0.0",
        openapi_tags=_TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    PREFIX = "/api/v1"
    app.include_router(health.router, prefix=PREFIX)
    app.include_router(resume.router, prefix=PREFIX)
    app.include_router(job_description.router, prefix=PREFIX)
    app.include_router(platform.router, prefix=PREFIX)
    app.include_router(memory.router, prefix=PREFIX)
    app.include_router(judge.router, prefix=PREFIX)
    app.include_router(code_run.router, prefix=PREFIX)
    app.include_router(session.router)

    @app.get("/", include_in_schema=False)
    async def api_root():
        return JSONResponse({
            "service": "Voice Interview Assistant API",
            "version": "1.0.0",
            "docs": "/docs",
            "ws": "/ws/session",
            "frontend": "Run the Next.js app: cd frontend && npm run dev",
        })

    return app


app = create_app()
