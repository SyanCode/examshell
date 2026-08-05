"""Terminal output helpers (colors, tables, diffs)."""

from __future__ import annotations

import os
import sys

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


def c(text: str, *styles: str) -> str:
    if not _USE_COLOR:
        return text
    prefix = "".join(_CODES[s] for s in styles)
    return f"{prefix}{text}{_CODES['reset']}"


def hline(char: str = "=", width: int = 60) -> str:
    return char * width


def visible(s: str, limit: int = 200) -> str:
    """Render a string with escaped control characters, truncated for display."""
    escaped = s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
    if len(escaped) > limit:
        escaped = escaped[:limit] + c("...(truncated)", "dim")
    return escaped


def format_timer(seconds_left: float) -> str:
    seconds_left = max(0, int(seconds_left))
    m, s = divmod(seconds_left, 60)
    text = f"{m:02d}:{s:02d}"
    if seconds_left <= 60:
        return c(text, "bold", "red")
    if seconds_left <= 5 * 60:
        return c(text, "yellow")
    return c(text, "green")
