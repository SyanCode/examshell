"""End-to-end validation: for every exercise, the reference solution must pass
all tests, and an empty stub must not."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from examshell.compiler import compile_student, find_forbidden_calls  # noqa: E402
from examshell.exercises import load_all  # noqa: E402
from examshell.runner import run_all  # noqa: E402

EXERCISES = load_all()


def _stub_source(ex):
    if ex.type == "program":
        return "int\tmain(void)\n{\n\treturn (0);\n}\n"
    # A well-typed but empty-bodied version of the function, so it compiles
    # cleanly (no missing-return warnings) but can't possibly pass the tests.
    proto = ex.prototype.replace(";", "").replace("\t", " ")
    if proto.strip().startswith("void"):
        body = "{\n}\n"
    else:
        body = "{\n\treturn (0);\n}\n"
    return f"{proto}\n{body}"


class ExerciseFixtureTests(unittest.TestCase):
    def test_at_least_16_exercises_loaded(self):
        self.assertGreaterEqual(len(EXERCISES), 16)

    def test_reference_solutions_pass(self):
        for ex_id, ex in EXERCISES.items():
            with self.subTest(exercise=ex_id):
                with tempfile.TemporaryDirectory(prefix="examshell-test-") as tmp:
                    workdir = Path(tmp)
                    src = workdir / ex.filename
                    src.write_text(ex.solution_path().read_text())
                    result = compile_student(ex, src, workdir / "build")
                    self.assertEqual(
                        result.forbidden_calls, [],
                        f"{ex_id}: reference solution flagged forbidden calls",
                    )
                    self.assertTrue(
                        result.success,
                        f"{ex_id}: reference solution failed to compile:\n{result.stderr}",
                    )
                    outcomes = run_all(result.binary_path, ex.tests)
                    failures = [
                        (o.test.argv, o.test.expected_stdout, o.actual_stdout, o.error)
                        for o in outcomes if not o.ok
                    ]
                    self.assertEqual(
                        failures, [],
                        f"{ex_id}: reference solution failed tests: {failures}",
                    )

    def test_empty_stub_does_not_fully_pass(self):
        for ex_id, ex in EXERCISES.items():
            with self.subTest(exercise=ex_id):
                with tempfile.TemporaryDirectory(prefix="examshell-test-") as tmp:
                    workdir = Path(tmp)
                    src = workdir / ex.filename
                    src.write_text(_stub_source(ex))
                    result = compile_student(ex, src, workdir / "build")
                    if not result.success:
                        continue  # compile failure also counts as "did not pass"
                    outcomes = run_all(result.binary_path, ex.tests)
                    all_ok = all(o.ok for o in outcomes)
                    self.assertFalse(all_ok, f"{ex_id}: empty stub unexpectedly passed all tests")

    def test_forbidden_function_detection(self):
        ex = EXERCISES["ft_putstr"]
        source = (
            "#include <string.h>\n"
            "void ft_putstr(char *str)\n"
            "{\n"
            "\t(void)strlen(str);\n"
            "}\n"
        )
        hits = find_forbidden_calls(source, ex.allowed_functions)
        self.assertIn("strlen", hits)

    def test_forbidden_function_ignored_inside_comment(self):
        ex = EXERCISES["ft_putstr"]
        source = (
            "/* do not call strlen(str) here */\n"
            "void ft_putstr(char *str)\n"
            "{\n"
            "\t(void)str;\n"
            "}\n"
        )
        hits = find_forbidden_calls(source, ex.allowed_functions)
        self.assertEqual(hits, [])

    def test_allowed_function_is_not_flagged(self):
        ex = EXERCISES["ft_putchar"]
        source = (
            "#include <unistd.h>\n"
            "void ft_putchar(char c)\n"
            "{\n"
            "\twrite(1, &c, 1);\n"
            "}\n"
        )
        hits = find_forbidden_calls(source, ex.allowed_functions)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
