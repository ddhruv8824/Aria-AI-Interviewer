#!/usr/bin/env python3
"""
Voice Interview Assistant — development launcher.

Starts:
  • FastAPI backend     (default :8000)
  • Auralis homepage    (default :4000)  — marketing / company selection
  • Interview app       (default :3000)  — voice + coding practice

Usage (from project root):
    python start.py
    python start.py --api-only
    python start.py --reload
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
AI_DIR = ROOT / "ai"
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
AURALIS_DIR = ROOT / "auralis"

API_HOST = os.getenv("HOST", "127.0.0.1")
API_PORT = int(os.getenv("PORT", "8000"))
HOME_PORT = int(os.getenv("HOME_PORT", "4000"))
APP_PORT = int(os.getenv("WEB_PORT", "3000"))

PROCS: list[subprocess.Popen] = []


def _print(msg: str) -> None:
    print(msg, flush=True)


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _python() -> str:
    venv_py = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    venv_py_unix = BACKEND_DIR / "venv" / "bin" / "python"
    if venv_py_unix.exists():
        return str(venv_py_unix)
    return sys.executable


def _npm() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def _shutdown(*_args) -> None:
    for proc in PROCS:
        if proc.poll() is None:
            proc.terminate()
    for proc in PROCS:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _ensure_npm_project(project_dir: Path, label: str, extra_check: Path | None = None) -> None:
    node_modules = project_dir / "node_modules"
    needs_install = not node_modules.exists()
    if extra_check and not extra_check.exists():
        needs_install = True
    if needs_install:
        _print(f"  Installing {label} dependencies…")
        subprocess.check_call([_npm(), "install"], cwd=project_dir, shell=sys.platform == "win32")


def _ensure_env(project_dir: Path) -> None:
    env_local = project_dir / ".env.local"
    env_example = project_dir / ".env.example"
    if not env_local.exists() and env_example.exists():
        env_local.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")


def start_backend(host: str, port: int, reload: bool) -> subprocess.Popen:
    cmd = [_python(), str(BACKEND_DIR / "api" / "server.py"), "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    return subprocess.Popen(cmd, cwd=BACKEND_DIR)


def start_next_app(project_dir: Path, host: str, port: int, env_extra: dict | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("PORT", str(port))
    if env_extra:
        env.update(env_extra)
    return subprocess.Popen(
        [_npm(), "run", "dev", "--", "--port", str(port)],
        cwd=project_dir,
        env=env,
        shell=sys.platform == "win32",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Voice Interview Assistant locally")
    parser.add_argument("--host", default=API_HOST)
    parser.add_argument("--port", type=int, default=API_PORT)
    parser.add_argument("--home-port", type=int, default=HOME_PORT, help="Auralis marketing site port")
    parser.add_argument("--web-port", type=int, default=APP_PORT, help="Interview app port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload backend")
    parser.add_argument("--api-only", action="store_true", help="Start backend only")
    parser.add_argument("--no-open", action="store_true", help="Do not open browser")
    args = parser.parse_args()

    host = args.host
    port = args.port
    home_port = args.home_port
    app_port = args.web_port

    if not AI_DIR.exists() or not BACKEND_DIR.exists():
        _print("  Missing ai/ or backend/ directory.")
        sys.exit(1)

    if _port_in_use(host, port):
        _print(f"  Port {port} is already in use on {host}.")
        sys.exit(1)

    if not args.api_only:
        for label, p in (("home", home_port), ("interview app", app_port)):
            if _port_in_use(host, p):
                _print(f"  Port {p} ({label}) is already in use on {host}.")
                sys.exit(1)

    if not args.api_only and not shutil.which("node"):
        _print("  Node.js is required for the Next.js apps.")
        sys.exit(1)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _print("\n" + "═" * 54)
    _print("  Auralis · Voice Interview Assistant")
    _print("═" * 54)

    PROCS.append(start_backend(host, port, reload=args.reload))
    _print(f"\n  API           : http://{host}:{port}/docs")

    if not args.api_only:
        if not AURALIS_DIR.exists():
            _print("  Missing auralis/ directory — skipping homepage.")
        else:
            _ensure_npm_project(AURALIS_DIR, "Auralis homepage", AURALIS_DIR / "node_modules" / "next")
            _ensure_env(AURALIS_DIR)
            PROCS.append(
                start_next_app(
                    AURALIS_DIR,
                    host,
                    home_port,
                    {
                        "NEXT_PUBLIC_API_URL": f"http://{host}:{port}",
                        "NEXT_PUBLIC_INTERVIEW_APP_URL": f"http://{host}:{app_port}",
                    },
                )
            )
            _print(f"  Homepage      : http://{host}:{home_port}/")

        _ensure_npm_project(FRONTEND_DIR, "interview app", FRONTEND_DIR / "node_modules" / "tailwindcss")
        _ensure_env(FRONTEND_DIR)
        PROCS.append(
            start_next_app(
                FRONTEND_DIR,
                host,
                app_port,
                {
                    "NEXT_PUBLIC_API_URL": f"http://{host}:{port}",
                    "NEXT_PUBLIC_HOME_URL": f"http://{host}:{home_port}",
                },
            )
        )
        _print(f"  Interview app : http://{host}:{app_port}/")

        if not args.no_open and AURALIS_DIR.exists():
            time.sleep(2)
            webbrowser.open(f"http://{host}:{home_port}/")

    _print("\n  Press Ctrl+C to stop.\n")

    try:
        while True:
            for proc in PROCS:
                code = proc.poll()
                if code is not None:
                    _print(f"  Process exited with code {code}. Shutting down.")
                    _shutdown()
                    sys.exit(code)
            time.sleep(0.5)
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
