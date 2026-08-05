"""Loading and representing exercises from data/exercises/*.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXERCISES_DIR = DATA_DIR / "exercises"
SOLUTIONS_DIR = DATA_DIR / "solutions"


@dataclass
class TestCase:
    argv: list
    expected_stdout: str
    stdin: str | None = None
    timeout: float = 5.0


@dataclass
class Exercise:
    id: str
    rank: int
    time_minutes: int
    title: str
    type: str  # "function" or "program"
    filename: str
    statement: str
    allowed_functions: list
    tests: list
    prototype: str | None = None
    harness: str | None = None

    def solution_path(self) -> Path:
        return SOLUTIONS_DIR / f"{self.id}.c"

    def skeleton(self) -> str:
        """Starter content written into the student's file the first time."""
        lines = []
        if self.type == "function":
            lines.append("#include <unistd.h>")
            lines.append("")
            lines.append(f"/* {self.prototype} */")
            lines.append("")
            allowed = ", ".join(self.allowed_functions) if self.allowed_functions else "(none)"
            lines.append(f"/* Allowed functions: {allowed} */")
            lines.append("")
        else:
            lines.append("#include <unistd.h>")
            lines.append("")
            allowed = ", ".join(self.allowed_functions) if self.allowed_functions else "(none)"
            lines.append(f"/* Allowed functions: {allowed} */")
            lines.append("")
            lines.append("int\tmain(void)")
            lines.append("{")
            lines.append("\treturn (0);")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)


def _load_one(path: Path) -> Exercise:
    data = json.loads(path.read_text())
    tests = [
        TestCase(
            argv=t.get("argv", []),
            expected_stdout=t["expected_stdout"],
            stdin=t.get("stdin"),
            timeout=t.get("timeout", 5.0),
        )
        for t in data["tests"]
    ]
    return Exercise(
        id=data["id"],
        rank=data["rank"],
        time_minutes=data["time_minutes"],
        title=data["title"],
        type=data["type"],
        filename=data["filename"],
        statement=data["statement"],
        allowed_functions=data.get("allowed_functions", []),
        tests=tests,
        prototype=data.get("prototype"),
        harness=data.get("harness"),
    )


def load_all() -> dict:
    exercises = {}
    for path in sorted(EXERCISES_DIR.glob("*.json")):
        ex = _load_one(path)
        exercises[ex.id] = ex
    return exercises


def by_rank(exercises: dict, rank: int) -> list:
    return sorted((e for e in exercises.values() if e.rank == rank), key=lambda e: e.id)
