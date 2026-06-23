"""
main.py
───────
Legacy CLI entry point (terminal + local mic/speakers).

For the full web UI on localhost, run from the project root instead:
    python start.py

CLI usage (optional):
    python main.py                              # no resume
    python main.py --resume path/to/resume.pdf  # with resume context

Requirements:
    pip install google-genai pyaudio langgraph langchain-core pdfplumber
"""

import argparse
import asyncio
import signal
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from shared.ui     import Colors, print_error
from core.assistant import VoiceAssistant


def main() -> None:
    # ── CLI args ─────────────────────────────────
    print("\n  Note: For the browser UI on localhost, use: python start.py  (from project root)\n")

    parser = argparse.ArgumentParser(
        description="Gemini Live Voice Interview Assistant"
    )
    parser.add_argument(
        "--resume",
        metavar="PATH",
        default=None,
        help="Path to a resume file (PDF or DOCX) to load into the assistant's context",
    )
    args = parser.parse_args()

    # ── Dependency pre-flight ────────────────────
    try:
        import pyaudio          # noqa: F401
    except ImportError:
        print_error("PyAudio not found.  Install: pip install pyaudio")
        sys.exit(1)

    try:
        # pyrefly: ignore [missing-import]
        from google import genai    # noqa: F401
    except ImportError:
        print_error("google-genai not found.  Install: pip install google-genai")
        sys.exit(1)

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import StateGraph  # noqa: F401
    except ImportError:
        print_error(
            "langgraph not found.  Install: pip install langgraph langchain-core"
        )
        sys.exit(1)

    # ── Bootstrap ────────────────────────────────
    assistant = VoiceAssistant(resume_path=args.resume)

    def _signal_handler(sig, frame) -> None:
        print(f"\n  {Colors.YELLOW}⏹  Stopping...{Colors.RESET}")
        assistant.stop()

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # ── Run ───────────────────────────────────────
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print(f"\n  {Colors.YELLOW}👋 Goodbye!{Colors.RESET}")


if __name__ == "__main__":
    main()