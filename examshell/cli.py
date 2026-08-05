"""Interactive shell, modeled loosely on the 42-school exam shell."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
import time
from pathlib import Path

from . import ui
from .exercises import Exercise, load_all
from .session import RANK_DURATION_MINUTES, Session, pick_exercises

DEFAULT_WORKSPACE = Path.cwd() / "examshell_workspace"


def _pick_editor() -> list:
    editor = os.environ.get("EDITOR")
    if editor:
        return editor.split()
    for candidate in ("nano", "vim", "vi"):
        path = shutil.which(candidate)
        if path:
            return [path]
    return None


def open_editor(path: Path) -> None:
    editor = _pick_editor()
    if editor is None:
        print(ui.c("No editor found (set $EDITOR). Edit the file yourself:", "yellow"))
        print(f"  {path}")
        input("Press Enter once you're done editing... ")
        return
    subprocess.call([*editor, str(path)])


def print_statement(ex: Exercise) -> None:
    print(ui.hline("-"))
    print(ui.c(f"{ex.title}", "bold", "cyan") + f"  (rank {ex.rank}, ~{ex.time_minutes} min)")
    print(ui.hline("-"))
    print(ex.statement.strip())
    if ex.prototype:
        print()
        print(ui.c("Prototype:", "bold"), ex.prototype)
    allowed = ", ".join(ex.allowed_functions) if ex.allowed_functions else "(none)"
    print(ui.c("Allowed functions:", "bold"), allowed)
    print(ui.c("File to edit:", "bold"), ex.filename)
    print(ui.hline("-"))


def print_test_report(ex_id: str, state) -> None:
    ex = state.exercise
    if state.forbidden_calls:
        print(ui.c(f"FORBIDDEN FUNCTION(S) USED: {', '.join(state.forbidden_calls)}", "bold", "red"))
        print("Your file calls a function that isn't in the allowed list for this exercise.")
        return
    if state.compile_error:
        print(ui.c("COMPILATION FAILED", "bold", "red"))
        print(textwrap.indent(state.compile_error.strip(), "  "))
        return

    for i, outcome in enumerate(state.outcomes, 1):
        tag = ui.c("OK", "green") if outcome.ok else ui.c("KO", "red")
        argv_repr = " ".join(outcome.test.argv) if outcome.test.argv else "(no args)"
        print(f"  [{tag}] test {i}: argv=({argv_repr})")
        if not outcome.ok:
            if outcome.error:
                print(f"        {ui.c(outcome.error, 'red')}")
            else:
                print(f"        expected: {ui.visible(outcome.test.expected_stdout)}")
                print(f"        actual:   {ui.visible(outcome.actual_stdout)}")

    if state.passed:
        print(ui.c(f"\n{ex.id}: PASSED ({state.tests_passed}/{state.tests_total})", "bold", "green"))
    else:
        print(ui.c(f"\n{ex.id}: FAILED ({state.tests_passed}/{state.tests_total})", "bold", "red"))


def print_board(session: Session) -> None:
    remaining = session.remaining_seconds()
    print(ui.hline("="))
    title = f"examshell — {session.name}"
    if remaining is not None:
        title += f"  |  time left: {ui.format_timer(remaining)}"
    print(ui.c(title, "bold"))
    print(ui.hline("="))
    for i, ex_id in enumerate(session.order, 1):
        state = session.states[ex_id]
        tag = state.status_tag()
        colored_tag = {"OK": ui.c("OK", "green"), "KO": ui.c("KO", "red"), " ": "  "}[tag]
        print(f" {i}) [{colored_tag}] {state.exercise.title:<20} {state.summary()}")
    print(ui.hline("-"))
    print("Commands: <n> edit exercise | t <n> test only | s <n> subject | r results | q quit")


def run_exam_loop(session: Session) -> None:
    while True:
        if session.expired():
            print(ui.c("\n⏰ Time's up! The exam ends here.", "bold", "red"))
            break
        print_board(session)
        try:
            cmd = input("> ").strip()
        except EOFError:
            break
        if not cmd:
            continue
        if session.expired():
            print(ui.c("\n⏰ Time's up! The exam ends here.", "bold", "red"))
            break

        parts = cmd.split()
        head = parts[0].lower()

        if head in ("q", "quit"):
            confirm = input("End the exam now? [y/N] ").strip().lower()
            if confirm == "y":
                break
            continue
        if head in ("r", "results"):
            for ex_id in session.order:
                st = session.states[ex_id]
                print(f"\n--- {st.exercise.title} ---")
                if st.attempts == 0:
                    print("  not attempted yet")
                else:
                    print_test_report(ex_id, st)
            continue

        if head in ("s", "subject") and len(parts) > 1:
            idx = _resolve_index(session, parts[1])
            if idx is not None:
                print_statement(session.states[session.order[idx]].exercise)
            continue

        if head in ("t", "test") and len(parts) > 1:
            idx = _resolve_index(session, parts[1])
            if idx is not None:
                ex_id = session.order[idx]
                print(f"\nCompiling and testing {ex_id}...")
                state = session.run_tests(ex_id)
                print_test_report(ex_id, state)
            continue

        idx = _resolve_index(session, head)
        if idx is not None:
            ex_id = session.order[idx]
            path = session.ensure_skeleton(ex_id)
            print_statement(session.states[ex_id].exercise)
            open_editor(path)
            print(f"\nCompiling and testing {ex_id}...")
            state = session.run_tests(ex_id)
            print_test_report(ex_id, state)
            continue

        print(ui.c("Unknown command.", "yellow"))

    final_report(session)


def _resolve_index(session: Session, token: str) -> int | None:
    if token.isdigit():
        i = int(token) - 1
        if 0 <= i < len(session.order):
            return i
    if token in session.order:
        return session.order.index(token)
    print(ui.c(f"No such exercise: {token}", "yellow"))
    return None


def final_report(session: Session) -> None:
    passed, total = session.score()
    report_path = session.save_report()
    print(ui.hline("="))
    print(ui.c("EXAM FINISHED", "bold"))
    print(ui.hline("="))
    for ex_id in session.order:
        st = session.states[ex_id]
        tag = ui.c("OK", "green") if st.passed else ui.c("KO", "red")
        print(f" [{tag}] {st.exercise.title:<20} {st.summary()}")
    print(ui.hline("-"))
    color = "green" if passed == total else ("yellow" if passed else "red")
    print(ui.c(f"Score: {passed}/{total} exercises fully passed", "bold", color))
    print(f"Report saved to: {report_path}")


def main_menu() -> None:
    exercises = load_all()
    while True:
        print(ui.hline("="))
        print(ui.c("examshell — C exam simulator", "bold", "cyan"))
        print(ui.hline("="))
        print(" 1) Timed exam (choose a rank)")
        print(" 2) Practice mode (no timer)")
        print(" q) Quit")
        choice = input("> ").strip().lower()

        if choice in ("q", "quit"):
            print("Bye!")
            return
        if choice == "1":
            start_exam_flow(exercises)
        elif choice == "2":
            practice_flow(exercises)
        else:
            print(ui.c("Unknown choice.", "yellow"))


def start_exam_flow(exercises: dict) -> None:
    ranks = sorted({e.rank for e in exercises.values()})
    print(f"Available ranks: {', '.join(str(r) for r in ranks)}")
    raw = input("Pick a rank: ").strip()
    if not raw.isdigit() or int(raw) not in ranks:
        print(ui.c("Invalid rank.", "yellow"))
        return
    rank = int(raw)
    chosen = pick_exercises(exercises, rank)
    duration = RANK_DURATION_MINUTES.get(rank, 90)
    print(f"\nRank {rank} exam: {len(chosen)} exercises, {duration} minutes.")
    print("Exercises: " + ", ".join(e.title for e in chosen))
    if input("Start now? [y/N] ").strip().lower() != "y":
        return

    session_name = f"exam-rank{rank}-{time.strftime('%Y%m%d-%H%M%S')}"
    workspace = DEFAULT_WORKSPACE / session_name
    session = Session(chosen, workspace, duration, session_name)
    run_exam_loop(session)


def practice_flow(exercises: dict) -> None:
    session_name = f"practice-{time.strftime('%Y%m%d-%H%M%S')}"
    workspace = DEFAULT_WORKSPACE / session_name
    all_exercises = sorted(exercises.values(), key=lambda e: (e.rank, e.id))
    session = Session(all_exercises, workspace, None, session_name)

    while True:
        print(ui.hline("="))
        print(ui.c("Practice mode", "bold", "cyan"), "(no timer)")
        for i, ex in enumerate(all_exercises, 1):
            st = session.states[ex.id]
            print(f" {i:>2}) [{st.status_tag():>2}] {ex.title:<22} rank {ex.rank}")
        print(ui.hline("-"))
        print("Commands: <n> practice exercise | sol <n> reveal solution | q back to main menu")
        cmd = input("> ").strip()
        if not cmd:
            continue
        parts = cmd.split()
        head = parts[0].lower()
        if head in ("q", "quit"):
            return
        if head == "sol" and len(parts) > 1:
            idx = _resolve_index(session, parts[1])
            if idx is not None:
                ex_id = session.order[idx]
                if input(f"Reveal the reference solution for {ex_id}? [y/N] ").strip().lower() == "y":
                    print(session.states[ex_id].exercise.solution_path().read_text())
            continue
        idx = _resolve_index(session, head)
        if idx is not None:
            ex_id = session.order[idx]
            practice_one(session, ex_id)


def practice_one(session: Session, ex_id: str) -> None:
    while True:
        path = session.ensure_skeleton(ex_id)
        print_statement(session.states[ex_id].exercise)
        open_editor(path)
        print(f"\nCompiling and testing {ex_id}...")
        state = session.run_tests(ex_id)
        print_test_report(ex_id, state)
        again = input("\n[Enter] edit again | b: back to menu > ").strip().lower()
        if again == "b":
            return
