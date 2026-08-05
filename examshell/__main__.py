from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import cli, ui
from .exercises import load_all
from .session import Session


def cmd_list(args) -> int:
    exercises = load_all()
    for ex in sorted(exercises.values(), key=lambda e: (e.rank, e.id)):
        print(f"rank {ex.rank}  {ex.id:<22} {ex.title}")
    return 0


def cmd_show(args) -> int:
    exercises = load_all()
    ex = exercises.get(args.id)
    if ex is None:
        print(f"Unknown exercise: {args.id}", file=sys.stderr)
        return 1
    cli.print_statement(ex)
    return 0


def cmd_test(args) -> int:
    exercises = load_all()
    ex = exercises.get(args.id)
    if ex is None:
        print(f"Unknown exercise: {args.id}", file=sys.stderr)
        return 1

    source_path = Path(args.file)
    if not source_path.exists():
        print(f"No such file: {source_path}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="examshell-") as tmp:
        workspace = Path(tmp)
        session = Session([ex], workspace, None, "cli-test")
        target = session.student_file(ex.id)
        target.write_text(source_path.read_text())
        state = session.run_tests(ex.id)
        cli.print_test_report(ex.id, state)
    return 0 if state.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="examshell", description="A 42-school-style C exam simulator.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list all available exercises")

    p_show = sub.add_parser("show", help="print an exercise's subject")
    p_show.add_argument("id")

    p_test = sub.add_parser("test", help="compile & test a .c file against an exercise, non-interactively")
    p_test.add_argument("id")
    p_test.add_argument("file")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "test":
        return cmd_test(args)

    cli.main_menu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
