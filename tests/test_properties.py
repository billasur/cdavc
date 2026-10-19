import ast
import json
import tempfile
import unittest
from pathlib import Path

from cdavc.mutants import kill_rate
from cdavc.properties import (
    PropertyTableError,
    _g_rpn,
    _rpn_divides_by_zero,
    entries_for,
    load_module,
    load_table,
    non_stdlib_imports,
    probe,
    replay_case,
    run_table,
)

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "benchmarks" / "properties.json"
SOLUTIONS = ROOT / "benchmarks" / "mock_solutions"
SEED = 20261019


class PropertyGateTests(unittest.TestCase):
    def _probe_source(self, task_id: str, source: str, *, seed: int = SEED) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solution.py"
            path.write_text(source)
            return probe(table_path=TABLE, task_id=task_id, files=[path], seed=seed)

    def test_table_covers_every_task_in_the_corpus(self):
        corpus = json.loads((ROOT / "benchmarks" / "tasks.json").read_text())["tasks"]
        table = load_table(TABLE)
        self.assertEqual({task["task_id"] for task in corpus}, set(table))
        for task_id, entries in table.items():
            self.assertTrue(entries_for(table, task_id), task_id)
            for entry in entries:
                self.assertIn("property", entry)

    def test_every_known_good_solution_passes_the_property_gate(self):
        """Cage-hurt guard: the oracle must never reject a reference solution."""

        for task_dir in sorted(SOLUTIONS.iterdir()):
            if not task_dir.is_dir():
                continue
            solution = task_dir / "solution.py"
            if not solution.is_file():
                continue
            result = probe(table_path=TABLE, task_id=task_dir.name, files=[solution], seed=SEED)
            self.assertTrue(result["ok"], f"{task_dir.name}: {result['failures'][:1]}")
            self.assertGreater(result["checked"], 0, task_dir.name)

    def test_merge_that_deduplicates_is_rejected(self):
        dedup = (
            "def merge_sorted(left: list, right: list) -> list:\n"
            "    result = []\n"
            "    for value in sorted(list(left) + list(right)):\n"
            "        if value not in result:\n"
            "            result.append(value)\n"
            "    return result\n"
        )
        result = self._probe_source("task_006", dedup)
        self.assertFalse(result["ok"])
        names = {failure["property"] for failure in result["failures"]}
        self.assertIn("merge_sorted_multiset", names)
        self.assertTrue(
            any("expected" in failure["message"] for failure in result["failures"]),
            result["failures"][:1],
        )

    def test_roman_without_validation_is_rejected(self):
        naive = (
            "VALUES = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n\n"
            "def roman_to_int(numeral: str) -> int:\n"
            "    total = 0\n"
            "    for index, character in enumerate(numeral):\n"
            "        value = VALUES[character]\n"
            "        if index + 1 < len(numeral) and VALUES[numeral[index + 1]] > value:\n"
            "            total -= value\n"
            "        else:\n"
            "            total += value\n"
            "    return total\n"
        )
        result = self._probe_source("task_015", naive)
        self.assertFalse(result["ok"])
        self.assertIn("IIII", json.dumps(result["failures"]))

    def test_purity_property_catches_argument_mutation(self):
        mutating = (
            "def unique_preserve(values: list) -> list:\n"
            "    result = []\n"
            "    for value in values:\n"
            "        if value not in result:\n"
            "            result.append(value)\n"
            "    values.reverse()\n"
            "    return result\n"
        )
        result = self._probe_source("task_008", mutating)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("mutated its arguments" in failure["message"] for failure in result["failures"]),
            result["failures"][:1],
        )

    def test_replay_reruns_a_previously_failing_input(self):
        dedup = (
            "def merge_sorted(left: list, right: list) -> list:\n"
            "    return sorted(set(list(left) + list(right)))\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solution.py"
            path.write_text(dedup)
            module = load_module([path])
        entry = load_table(TABLE)["task_006"][0]
        failure = replay_case(module, entry, [[1], [1]])
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.arguments, ([1], [1]))
        self.assertIn("expected", failure.message)

        good = "def merge_sorted(left: list, right: list) -> list:\n    return sorted(list(left) + list(right))\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solution.py"
            path.write_text(good)
            module = load_module([path])
        self.assertIsNone(replay_case(module, entry, [[1], [1]]))

    def test_rpn_generator_never_emits_a_zero_divisor(self):
        """Regression: this exact shape used to make the oracle divide by zero."""

        self.assertTrue(_rpn_divides_by_zero(["-3", "-5", "-1", "-4", "/", "/", "-"]))
        entry = load_table(TABLE)["task_028"][0]
        import random

        for seed in range(40):
            rng = random.Random(f"{seed}:rpn_reference")
            for arguments in _g_rpn(entry, rng, 24):
                self.assertFalse(
                    _rpn_divides_by_zero(arguments[0]),
                    f"seed {seed} emitted a zero divisor: {arguments[0]}",
                )
        for task_dir in (SOLUTIONS / "task_028",):
            for seed in range(10):
                result = probe(
                    table_path=TABLE,
                    task_id="task_028",
                    files=[task_dir / "solution.py"],
                    seed=seed,
                )
                self.assertTrue(result["ok"], f"seed {seed}: {result['failures'][:1]}")

    def test_mutant_kill_rate_is_measured_against_the_same_table(self):
        source = (SOLUTIONS / "task_006" / "solution.py").read_text()
        entries = load_table(TABLE)["task_006"]
        report = kill_rate([source], entries, run_table=run_table, seed=SEED, limit=4)
        self.assertGreater(report["generated"], 0)
        self.assertGreaterEqual(report["killed"], 1)
        self.assertLessEqual(report["killed"], report["generated"])
        self.assertGreaterEqual(report["kill_rate"], 0.0)
        self.assertLessEqual(report["kill_rate"], 1.0)

    def test_hanging_mutant_is_bounded_and_counted_as_killed(self):
        import time

        def hanging(_module, _entries, *, seed=0, replay=()):
            time.sleep(30)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solution.py"
            path.write_text((SOLUTIONS / "task_021" / "solution.py").read_text())
            source = path.read_text()
        entries = load_table(TABLE)["task_021"]
        started = time.perf_counter()
        report = kill_rate([source], entries, run_table=hanging, seed=SEED, limit=2, timeout=0.1)
        elapsed = time.perf_counter() - started
        self.assertGreater(report["generated"], 0)
        self.assertEqual(report["killed"], report["generated"])
        self.assertTrue(report["timeouts"])
        self.assertLess(elapsed, 5.0)

    def test_mutant_metric_cannot_reject_a_correct_candidate(self):
        """Regression: a hanging mutant used to fail task_021's whole verdict."""

        result = probe(
            table_path=TABLE,
            task_id="task_021",
            files=[SOLUTIONS / "task_021" / "solution.py"],
            seed=SEED,
            mutants=3,
            mutant_timeout=0.1,
        )
        self.assertTrue(result["ok"], result["failures"][:1])
        self.assertIsNotNone(result["mutants"]["kill_rate"])

    def test_non_stdlib_imports_respects_the_local_allowlist(self):
        tree = ast.parse("import numpy\nfrom helper import VALUE\nimport json\n")
        self.assertEqual(non_stdlib_imports(tree), ["helper", "numpy"])
        self.assertEqual(non_stdlib_imports(tree, allowed=("numpy", "helper")), [])

    def test_malformed_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.json"
            path.write_text(json.dumps({"tasks": {"task_001": [{"property": "not_a_property"}]}}))
            with self.assertRaises(PropertyTableError):
                load_table(path)
            path.write_text(json.dumps({"tasks": {"task_015": [{"property": "roman_parse_corpus"}]}}))
            with self.assertRaises(PropertyTableError):
                load_table(path)


if __name__ == "__main__":
    unittest.main()
