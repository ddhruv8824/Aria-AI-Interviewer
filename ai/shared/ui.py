"""
shared/ui.py
────────────
Terminal UI helpers for the Gemini Live Voice Interview Assistant.
Keeps all ANSI colour codes and print formatting in one place so every
other module gets consistent output by importing from here.
"""


# ──────────────────────────────────────────────
# ANSI colour constants
# ──────────────────────────────────────────────
class Colors:
    HEADER  = "\033[95m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"
    MAGENTA = "\033[35m"


# ──────────────────────────────────────────────
# Print helpers
# ──────────────────────────────────────────────
def print_banner(model: str, voice: str) -> None:
    """Render the startup banner with model and voice info."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║   🎙️  Gemini Live Voice Interview Assistant          ║
    ║                                                      ║
    ║   Model: {model:<35}     ║
    ║   Voice: {voice:<35}     ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)


def print_status(message: str, color: str = Colors.DIM) -> None:
    """Informational line — used for setup steps and state changes."""
    print(f"  {color}● {message}{Colors.RESET}")


def print_event(message: str, color: str = Colors.GREEN) -> None:
    """Event line — used for runtime activity (mic active, turn complete, …)."""
    print(f"  {color}► {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Error line — always rendered in red."""
    print(f"  {Colors.RED}✖ {message}{Colors.RESET}")
