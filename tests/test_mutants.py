"""Unit tests for cdavc.mutants (experiment 4 hand-mutant kill rate)."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from cdavc.mutants import (
    generate_mutants,
    main,
    run_task,
    wilson_interval,
)

TOY_SOURCE = textwrap.dedent(
    '''
    def clamp_count(xs, lo, hi):
        count = 0
        for x in xs:
            if lo <= x and x < hi:
                count = count + 1
        return count
    '''
).lstrip()


class GenerateMutantsTest(unittest.TestCase):
    def test_deterministic(self):
        first = generate_mutants(TOY_SOURCE)
        second = generate_mutants(TOY_SOURCE)
        self.assertEqual([m.source for m in first], [m.source for m in second])

    def test_no_duplicates_and_all_compile(self):
        mutants = generate_mutants(TOY_SOURCE)
        sources = [m.source for m in mutants]
        self.assertEqual(len(sources), len(set(sources)))
        self.assertNotIn(TOY_SOURCE, sources)
        for mutant in mutants:
            compile(mutant.source, "<mutant>", "exec")

    def test_expected_operators_present(self):
        mutants = generate_mutants(TOY_SOURCE)
        operators = {m.operator for m in mutants}
        self.assertIn("compare_swap", operators)
        self.assertIn("const_shift", operators)
        self.assertIn("negate_test", operators)

    def test_comparison_swap_is_applied(self):
        mutants = generate_mutants("def f(a, b):\n    return a < b\n")
        swapped = [m for m in mutants if m.operator == "compare_swap"]
        self.assertEqual(len(swapped), 1)
        self.assertIn("a <= b", swapped[0].source)

    def test_constant_shift_both_directions(self):
        mutants = generate_mutants("def f(xs):\n    return len(xs) + 1\n")
        shifts = sorted(m.source for m in mutants if m.operator == "const_shift")
        self.assertEqual(len(shifts), 2)
        self.assertTrue(any("+ 2" in src for src in shifts))
        self.assertTrue(any("+ 0" in src for src in shifts))

    def test_booleans_are_not_shifted(self):
        mutants = generate_mutants("def f():\n    return True\n")
        self.assertEqual(mutants, [])

    def test_ids_are_sequential(self):
        mutants = generate_mutants(TOY_SOURCE)
        self.assertEqual([m.mutant_id for m in mutants], [f"m{i:04d}" for i in range(len(mutants))])


class WilsonIntervalTest(unittest.TestCase):
    def test_known_value(self):
        # Hand-computed Wilson 95% interval for 8/10: centre 0.7167,
        # margin 0.2266, giving (0.4902, 0.9433).
        lo, hi = wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.4902, places=3)
        self.assertAlmostEqual(hi, 0.9433, places=3)

    def test_edges(self):
        lo, hi = wilson_interval(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        lo, hi = wilson_interval(10, 10)
        self.assertAlmostEqual(hi, 1.0)
        self.assertGreater(lo, 0.0)

    def test_empty(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))


HIDDEN_TESTS_TEMPLATE = textwrap.dedent(
    '''
    import importlib.util
    import sys
    from pathlib import Path

    def load():
        path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "reference_solution.py"
        spec = importlib.util.spec_from_file_location("candidate", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    if __name__ == "__main__":
        m = load()
        try:
            assert m.clamp_count([0, 5, 10, 15], 5, 10) == 1
            assert m.clamp_count([], 0, 1) == 0
            assert m.clamp_count([5], 5, 6) == 1
            assert m.clamp_count([10], 5, 10) == 0
        except Exception as exc:
            print(f"hidden test failed: {exc}", file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0)
    '''
).lstrip()


class RunTaskTest(unittest.TestCase):
    def _make_task(self, reference: str, hidden: str) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="cdavc_test_task_"))
        (tmp / "reference_solution.py").write_text(reference, encoding="utf-8")
        (tmp / "hidden_tests.py").write_text(hidden, encoding="utf-8")
        return tmp

    def test_kills_boundary_mutant(self):
        task_dir = self._make_task(TOY_SOURCE, HIDDEN_TESTS_TEMPLATE)
        result = run_task(task_dir, timeout=10.0)
        self.assertTrue(result.reference_passes)
        self.assertGreater(result.mutants_total, 0)
        self.assertIsNotNone(result.kill_rate)
        # The `lo <= x` -> `lo < x` swap turns clamp_count([5], 5, 6) into 0.
        compare_mutants = [o for o in result.outcomes if o.operator == "compare_swap"]
        self.assertTrue(compare_mutants)
        self.assertTrue(any(o.status == "killed" for o in compare_mutants))

    def test_survivor_reported_when_tests_are_weak(self):
        # Only the empty-input check remains, so boundary mutants survive.
        weak_hidden = (
            "import importlib.util, sys\n"
            "from pathlib import Path\n"
            "def load():\n"
            "    path = Path(sys.argv[1])\n"
            "    spec = importlib.util.spec_from_file_location('candidate', path)\n"
            "    module = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(module)\n"
            "    return module\n"
            "if __name__ == '__main__':\n"
            "    m = load()\n"
            "    try:\n"
            "        assert m.clamp_count([], 0, 1) == 0\n"
            "    except Exception as exc:\n"
            "        print(f'hidden test failed: {exc}', file=sys.stderr)\n"
            "        raise SystemExit(1)\n"
            "    raise SystemExit(0)\n"
        )
        task_dir = self._make_task(TOY_SOURCE, weak_hidden)
        result = run_task(task_dir, timeout=10.0)
        self.assertTrue(result.reference_passes)
        # With the boundary assertions removed, a comparison swap survives.
        self.assertGreater(result.survived, 0)
        self.assertLess(result.kill_rate, 1.0)

    def test_reference_failure_skips_task(self):
        task_dir = self._make_task("def clamp_count(xs, lo, hi):\n    return 0\n", HIDDEN_TESTS_TEMPLATE)
        result = run_task(task_dir, timeout=10.0)
        self.assertFalse(result.reference_passes)
        self.assertIsNone(result.kill_rate)
        self.assertEqual(result.mutants_total, 0)

    def test_max_mutants_stride_subsample(self):
        task_dir = self._make_task(TOY_SOURCE, HIDDEN_TESTS_TEMPLATE)
        full = run_task(task_dir, timeout=10.0)
        capped = run_task(task_dir, timeout=10.0, max_mutants=3)
        self.assertEqual(capped.mutants_total, 3)
        capped_ids = {o.mutant_id for o in capped.outcomes}
        full_ids = {o.mutant_id for o in full.outcomes}
        self.assertTrue(capped_ids <= full_ids)


class MainTest(unittest.TestCase):
    def test_main_writes_report(self):
        with tempfile.TemporaryDirectory(prefix="cdavc_test_root_") as tmp:
            root = Path(tmp)
            task_dir = root / "agent1" / "task_x"
            task_dir.mkdir(parents=True)
            (task_dir / "reference_solution.py").write_text(TOY_SOURCE, encoding="utf-8")
            (task_dir / "hidden_tests.py").write_text(HIDDEN_TESTS_TEMPLATE, encoding="utf-8")
            out = root / "report.json"
            self.assertEqual(main(["--root", str(root), "--out", str(out)]), 0)
            import json

            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(report["tasks"]), 1)
            self.assertGreater(report["overall"]["mutants"], 0)
            self.assertIsNotNone(report["overall"]["wilson95"])


if __name__ == "__main__":
    unittest.main()
