"""Running a compiled exercise binary against its test cases."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .exercises import TestCase


@dataclass
class TestOutcome:
    test: TestCase
    ok: bool
    actual_stdout: str
    error: str | None = None


def run_test(binary_path: Path, test: TestCase) -> TestOutcome:
    try:
        proc = subprocess.run(
            [str(binary_path), *test.argv],
            input=test.stdin.encode() if test.stdin is not None else None,
            capture_output=True,
            timeout=test.timeout,
        )
    except subprocess.TimeoutExpired:
        return TestOutcome(test, False, "", error=f"timeout (> {test.timeout}s), possible infinite loop")

    if proc.returncode < 0:
        return TestOutcome(
            test, False, "", error=f"crashed (signal {-proc.returncode})"
        )

    actual = proc.stdout.decode(errors="replace")
    ok = actual == test.expected_stdout
    return TestOutcome(test, ok, actual)


def run_all(binary_path: Path, tests: list) -> list:
    return [run_test(binary_path, t) for t in tests]
