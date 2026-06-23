"""
api/server.py
──────────────
Uvicorn entry point for the Voice Interview Assistant REST API.

Usage (prefer the root launcher):
    python start.py                         # from project root (recommended)

Or run the API only:
    python api/server.py                    # default: localhost:8000
    python api/server.py --host 0.0.0.0 --port 8080
    uvicorn api.app:app --reload            # dev mode with auto-reload

Environment variables (optional overrides):
    HOST   default: 127.0.0.1
    PORT   default: 8000
    RELOAD default: false
"""

import argparse
import os
import sys
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AI_DIR = str(_PROJECT_ROOT / "ai")
_BACKEND_DIR = str(_PROJECT_ROOT / "backend")
for path in (_AI_DIR, _BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

# pyrefly: ignore [missing-import]
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Voice Interview Assistant — FastAPI server"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() == "true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1; use >1 for production)",
    )
    args = parser.parse_args()

    print(f"\n  Starting Voice Interview Assistant API")
    print(f"  Host    : {args.host}")
    print(f"  Port    : {args.port}")
    print(f"  Reload  : {args.reload}")
    print(f"  Workers : {args.workers}")
    print(f"\n  Docs   : http://{args.host}:{args.port}/docs")
    print(f"  ReDoc  : http://{args.host}:{args.port}/redoc\n")

    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info",
        ws_ping_interval=None,
        ws_ping_timeout=None,
    )


if __name__ == "__main__":
    main()
