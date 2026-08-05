"""Exam / practice session state: workspace, timer, scoring."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from .compiler import CompileResult, compile_student
from .exercises import Exercise
from .runner import TestOutcome, run_all

# Suggested exam length per rank, mirroring the increasing duration of real
# 42 exams as the rank goes up.
RANK_DURATION_MINUTES = {1: 60, 2: 90, 3: 120}
RANK_EXERCISE_COUNT = {1: 3, 2: 4, 3: 4}


@dataclass
class ExerciseState:
    exercise: Exercise
    attempts: int = 0
    tests_passed: int = 0
    tests_total: int = 0
    passed: bool = False
    compile_error: str | None = None
    forbidden_calls: list = field(default_factory=list)
    outcomes: list = field(default_factory=list)

    def status_tag(self) -> str:
        if self.attempts == 0:
            return " "
        if self.passed:
            return "OK"
        return "KO"

    def summary(self) -> str:
        if self.attempts == 0:
            return "not started"
        if self.compile_error:
            return "compile error"
        if self.forbidden_calls:
            return f"forbidden: {', '.join(self.forbidden_calls)}"
        return f"{self.tests_passed}/{self.tests_total} tests"


class Session:
    def __init__(self, exercises: list, workspace: Path, duration_minutes: int | None, name: str):
        self.states = {e.id: ExerciseState(exercise=e) for e in exercises}
        self.order = [e.id for e in exercises]
        self.workspace = workspace
        self.duration_minutes = duration_minutes
        self.name = name
        self.start_time = time.time()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def exercise_dir(self, ex_id: str) -> Path:
        d = self.workspace / ex_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def student_file(self, ex_id: str) -> Path:
        ex = self.states[ex_id].exercise
        return self.exercise_dir(ex_id) / ex.filename

    def ensure_skeleton(self, ex_id: str) -> Path:
        path = self.student_file(ex_id)
        if not path.exists():
            path.write_text(self.states[ex_id].exercise.skeleton())
        return path

    def remaining_seconds(self) -> float | None:
        if self.duration_minutes is None:
            return None
        elapsed = time.time() - self.start_time
        return self.duration_minutes * 60 - elapsed

    def expired(self) -> bool:
        remaining = self.remaining_seconds()
        return remaining is not None and remaining <= 0

    def run_tests(self, ex_id: str) -> ExerciseState:
        state = self.states[ex_id]
        ex = state.exercise
        student_path = self.ensure_skeleton(ex_id)
        build_dir = self.exercise_dir(ex_id) / ".build"

        state.attempts += 1
        result: CompileResult = compile_student(ex, student_path, build_dir)

        if result.forbidden_calls:
            state.compile_error = None
            state.forbidden_calls = result.forbidden_calls
            state.passed = False
            state.tests_total = len(ex.tests)
            state.tests_passed = 0
            state.outcomes = []
            return state

        state.forbidden_calls = []

        if not result.success:
            state.compile_error = result.stderr
            state.passed = False
            state.tests_total = len(ex.tests)
            state.tests_passed = 0
            state.outcomes = []
            return state

        state.compile_error = None
        outcomes: list = run_all(result.binary_path, ex.tests)
        state.outcomes = outcomes
        state.tests_total = len(outcomes)
        state.tests_passed = sum(1 for o in outcomes if o.ok)
        state.passed = state.tests_passed == state.tests_total
        return state

    def score(self) -> tuple:
        passed = sum(1 for s in self.states.values() if s.passed)
        return passed, len(self.states)

    def save_report(self) -> Path:
        report = {
            "name": self.name,
            "started_at": self.start_time,
            "duration_minutes": self.duration_minutes,
            "results": {
                ex_id: {
                    "title": st.exercise.title,
                    "rank": st.exercise.rank,
                    "attempts": st.attempts,
                    "passed": st.passed,
                    "tests_passed": st.tests_passed,
                    "tests_total": st.tests_total,
                    "summary": st.summary(),
                }
                for ex_id, st in self.states.items()
            },
        }
        path = self.workspace / "report.json"
        path.write_text(json.dumps(report, indent=2))
        return path


def pick_exercises(exercises: dict, rank: int, count: int | None = None) -> list:
    from .exercises import by_rank

    pool = by_rank(exercises, rank)
    if count is None:
        count = RANK_EXERCISE_COUNT.get(rank, min(4, len(pool)))
    count = min(count, len(pool))
    return random.sample(pool, count)
