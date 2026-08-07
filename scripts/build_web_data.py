#!/usr/bin/env python3
"""Bundle data/exercises/*.json and data/solutions/*.c into pages/data/.

GitHub Pages only serves static files, so the browser can't list a
directory the way examshell.exercises.load_all() does on disk. This
script produces one exercises.json array (same fields as the CLI's
Exercise dataclass) plus a copy of each reference solution, both under
pages/data/, so the web app can just fetch() them.

Run it whenever data/exercises or data/solutions change; the GitHub
Pages deploy workflow also runs it on every deploy so pages/data/ never
goes stale relative to data/.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXERCISES_DIR = ROOT / "data" / "exercises"
SOLUTIONS_DIR = ROOT / "data" / "solutions"
OUT_DIR = ROOT / "pages" / "data"


def main() -> int:
    exercises = []
    for path in sorted(EXERCISES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        required = ("id", "rank", "time_minutes", "title", "type", "filename", "statement", "tests")
        missing = [k for k in required if k not in data]
        if missing:
            print(f"error: {path}: missing fields {missing}", file=sys.stderr)
            return 1
        exercises.append(data)

    out_solutions = OUT_DIR / "solutions"
    if out_solutions.exists():
        shutil.rmtree(out_solutions)
    out_solutions.mkdir(parents=True)

    for ex in exercises:
        solution_path = SOLUTIONS_DIR / f"{ex['id']}.c"
        if not solution_path.exists():
            print(f"error: missing solution for {ex['id']}: {solution_path}", file=sys.stderr)
            return 1
        shutil.copy(solution_path, out_solutions / solution_path.name)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "exercises.json").write_text(json.dumps(exercises, indent=2) + "\n")

    print(f"wrote {len(exercises)} exercises to {OUT_DIR / 'exercises.json'}")
    print(f"copied {len(exercises)} solutions to {out_solutions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
