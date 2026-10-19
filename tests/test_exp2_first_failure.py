"""Experiment 2 (night-run): first-failure-only repair feedback.

Unit tests for the single change in src/cdavc/benchmark.py: the cage repair
prompt now carries `_first_failure_excerpt(detail)` instead of the full
sanitised gate output.  Research basis: SWE-agent (arXiv:2405.15793) -
concise, structured tool feedback helps agents more than raw output dumps.

Status: prepared, not measured.  These are unit checks, not a benchmark run.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cdavc.benchmark import BenchmarkRunner, BenchmarkTask, _first_failure_excerpt
from cdavc.providers import MockProvider

UNITTEST_OUTPUT = (
    "F.F\n"
    "======================================================================\n"
    "FAIL: test_empty (test_solution.TestThing)\n"
    "----------------------------------------------------------------------\n"
    "Traceback (most recent call last):\n"
    '  File "$WORKSPACE/tests/test_solution.py", line 12, in test_empty\n'
    "    self.assertEqual(thing([]), [])\n"
    "AssertionError: [] != None\n"
    "\n"
    "======================================================================\n"
    "FAIL: test_roundtrip (test_solution.TestThing)\n"
    "----------------------------------------------------------------------\n"
    "Traceback (most recent call last):\n"
    '  File "$WORKSPACE/tests/test_solution.py", line 20, in test_roundtrip\n'
    "    self.assertEqual(thing([1]), [1])\n"
    "AssertionError: [1] != [2]\n"
    "\n"
    "----------------------------------------------------------------------\n"
    "Ran 3 tests in 0.001s\n"
    "\n"
    "FAILED (failures=2)\n"
)


class FirstFailureExcerptTests(unittest.TestCase):
    def test_unittest_output_keeps_only_first_failure_block(self):
        excerpt = _first_failure_excerpt(UNITTEST_OUTPUT)
        self.assertIn("FAIL: test_empty", excerpt)
        self.assertIn("AssertionError: [] != None", excerpt)
        self.assertNotIn("test_roundtrip", excerpt)
        self.assertNotIn("[1] != [2]", excerpt)

    def test_noise_before_failure_line_is_dropped(self):
        output = (
            "loading weights...\n"
            "warmup done\n"
            "public test failed for task_001: expected 3, got 2\n"
        )
        excerpt = _first_failure_excerpt(output)
        self.assertEqual(excerpt, "public test failed for task_001: expected 3, got 2")

    def test_single_line_failure_is_unchanged(self):
        output = "regression test failed for task_002: expected True, got False"
        self.assertEqual(_first_failure_excerpt(output), output)

    def test_traceback_keeps_exception_line(self):
        output = (
            "importing candidate\n"
            "Traceback (most recent call last):\n"
            '  File "$WORKSPACE/src/solution.py", line 3, in <module>\n'
            "    x = 1 +\n"
            "SyntaxError: invalid syntax\n"
        )
        excerpt = _first_failure_excerpt(output)
        self.assertIn("Traceback (most recent call last):", excerpt)
        self.assertIn("SyntaxError: invalid syntax", excerpt)
        self.assertNotIn("importing candidate", excerpt)

    def test_empty_output_stays_empty(self):
        self.assertEqual(_first_failure_excerpt(""), "")
        self.assertEqual(_first_failure_excerpt("   \n  "), "")

    def test_unrecognised_output_is_returned_bounded(self):
        output = "x" * 5000
        excerpt = _first_failure_excerpt(output)
        self.assertLessEqual(len(excerpt), 820)
        self.assertIn("[...]", excerpt)

    def test_long_block_keeps_head_and_assertion_tail(self):
        middle = "".join(f'  File "$WORKSPACE/src/solution.py", line {i}, in f{i}\n' for i in range(200))
        output = (
            "======================================================================\n"
            "FAIL: test_big (test_solution.TestThing)\n"
            "----------------------------------------------------------------------\n"
            "Traceback (most recent call last):\n"
            + middle
            + "AssertionError: final answer wrong\n"
        )
        excerpt = _first_failure_excerpt(output)
        self.assertIn("FAIL: test_big", excerpt)
        self.assertIn("AssertionError: final answer wrong", excerpt)
        self.assertIn("[...]", excerpt)
        self.assertLessEqual(len(excerpt), 820)

    def test_max_chars_is_configurable(self):
        excerpt = _first_failure_excerpt(UNITTEST_OUTPUT, max_chars=120)
        self.assertLessEqual(len(excerpt), 140)


class CageRepairExcerptTests(unittest.TestCase):
    """The repair prompt carries the excerpt, never the full dump."""

    def _runner(self, root: Path) -> BenchmarkRunner:
        task = BenchmarkTask(
            task_id="answer",
            title="Implement the answer function",
            description="Return the input value plus one.",
            source="test-fixture-v1",
            implementation_files=("src/answer.py",),
            test_files=("tests/test_answer.py",),
            symbols=("answer",),
            test_command=("python", "-m", "unittest", "tests.test_answer"),
            regression_command=("python", "-m", "unittest", "discover", "-s", "tests"),
            max_retries=1,
        )
        return BenchmarkRunner(
            root,
            MockProvider(['{"files": {"src/answer.py": "def answer():\\n    return 42\\n"}}']),
            tasks=[task],
            records_path=root / "records.jsonl",
        )

    def test_cage_repair_prompt_uses_first_failure_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = self._runner(root)
            task = runner.tasks[0]
            noisy = "loading weights...\n" + UNITTEST_OUTPUT
            prompt = runner._cage_repair(task, f"targeted test failed:\n{noisy}")
            self.assertIn("FAIL: test_empty", prompt)
            self.assertNotIn("test_roundtrip", prompt)
            self.assertNotIn("loading weights", prompt)

    def test_hidden_gate_stays_categorical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = self._runner(root)
            task = runner.tasks[0]
            prompt = runner._cage_repair(task, "hidden test failed")
            self.assertNotIn("Public gate output", prompt)
            self.assertNotIn("FAIL:", prompt)


if __name__ == "__main__":
    unittest.main()
