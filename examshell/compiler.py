"""Strict compilation and forbidden-function checks, in the spirit of the 42 exam moulinette."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .exercises import Exercise

CFLAGS = ["-Wall", "-Wextra", "-Werror", "-std=gnu99"]

# Functions that a 42-style exam commonly bans unless explicitly allowed
# for a given exercise (e.g. "write" for output-only exercises).
BLACKLIST = [
    "printf", "fprintf", "sprintf", "snprintf", "vprintf",
    "puts", "putchar", "putc", "fputs", "fputc",
    "malloc", "calloc", "realloc", "free",
    "strlen", "strcpy", "strncpy", "strcat", "strncat",
    "strcmp", "strncmp", "strdup", "strchr", "strrchr", "strstr",
    "memcpy", "memmove", "memset", "memcmp",
    "atoi", "atol", "exit", "abort", "system",
]


@dataclass
class CompileResult:
    success: bool
    binary_path: Path | None
    stderr: str
    forbidden_calls: list = field(default_factory=list)


def _strip_comments_and_strings(src: str) -> str:
    """Best-effort removal of comments/string/char literals so the forbidden-function
    grep doesn't trip on identifiers that only appear in text."""
    out = []
    i = 0
    n = len(src)
    while i < n:
        two = src[i : i + 2]
        if two == "/*":
            end = src.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if two == "//":
            end = src.find("\n", i + 2)
            i = n if end == -1 else end
            continue
        c = src[i]
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\\":
                    j += 1
                j += 1
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                if src[j] == "\\":
                    j += 1
                j += 1
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def find_forbidden_calls(source: str, allowed_functions: list) -> list:
    cleaned = _strip_comments_and_strings(source)
    banned = [f for f in BLACKLIST if f not in allowed_functions]
    hits = []
    for func in banned:
        if re.search(rf"\b{re.escape(func)}\s*\(", cleaned):
            hits.append(func)
    return hits


def compile_student(exercise: Exercise, student_path: Path, workdir: Path) -> CompileResult:
    source = student_path.read_text()
    forbidden = find_forbidden_calls(source, exercise.allowed_functions)

    workdir.mkdir(parents=True, exist_ok=True)
    binary_path = workdir / "a.out"
    sources = [str(student_path)]

    if exercise.type == "function":
        harness_path = workdir / "_harness.c"
        harness_path.write_text(exercise.harness)
        sources.append(str(harness_path))

    if forbidden:
        return CompileResult(False, None, "", forbidden_calls=forbidden)

    cmd = ["gcc", *CFLAGS, *sources, "-o", str(binary_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return CompileResult(False, None, proc.stderr, forbidden_calls=[])
    return CompileResult(True, binary_path, proc.stderr, forbidden_calls=[])
