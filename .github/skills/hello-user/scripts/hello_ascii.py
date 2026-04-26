#!/usr/bin/env python3
"""Generate an ASCII art greeting for the current user.

Usage:
    python hello_ascii.py              # auto-detects username
    python hello_ascii.py "Alice"      # use a specific username
"""

import os
import subprocess
import sys


def get_username(override: str | None = None) -> str:
    """Return the active username, optionally overridden by the caller."""
    if override:
        return override

    # Environment variables cover Windows, Linux, and macOS.
    for var in ("USERNAME", "USER", "LOGNAME"):
        value = os.environ.get(var)
        if value:
            return value

    # Last resort: ask the OS.
    try:
        result = subprocess.run(
            ["whoami"], capture_output=True, text=True, timeout=5
        )
        name = result.stdout.strip()
        # Windows returns DOMAIN\username — keep only the username part.
        return name.split("\\")[-1] if "\\" in name else name
    except Exception:
        return "User"


def render(text: str) -> str:
    """Render *text* as ASCII art.

    Uses pyfiglet's 'standard' font for a consistent look every time.
    Falls back to a simple banner if pyfiglet is not installed.
    """
    try:
        import pyfiglet  # type: ignore

        return pyfiglet.figlet_format(text, font="standard")
    except ImportError:
        bar = "=" * (len(text) + 4)
        return f"\n{bar}\n  {text}  \n{bar}\n"


def main() -> None:
    username = get_username(sys.argv[1] if len(sys.argv) > 1 else None)
    greeting = f"Hello, {username}!"
    print(render(greeting))


if __name__ == "__main__":
    main()
