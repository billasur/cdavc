import dataclasses
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cdavc.properties import PropertyCase, evaluate_properties


# Frozen fixtures deliberately include misleading AST evidence.
FIXTURES = (
    ("good.py", "def check(x):\n    if x < 0: raise ValueError('negative')\n    return x * 2\n"),
    ("unrelated.py", "def other(): raise ValueError()\ndef check(x): return x\n"),
    ("unreachable.py", "def check(x):\n    return x\n    raise ValueError()\n"),
    ("mutate.py", "def check(x):\n    x.append(2)\n    return len(x)\n"),
    ("broken.py", "import missing_cdavc_property_dependency\n"),
    ("slow.py", "def check(x):\n    while True: pass\n"),
    ("state.py", "count = 0\ndef check(x):\n    global count\n    count += 1\n    return count\n"),
)


class PropertyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, source in FIXTURES:
            (self.root / name).write_text(source)

    def case(self, file="good.py", **updates):
        value = dict(name="negative", file=file, symbol="check", args=[-1], kwargs={}, raises="ValueError")
        value.update(updates)
        return value

    def test_actual_exception_required_and_evidence_deterministic(self):
        cases = [self.case(file=name) for name in ("good.py", "unrelated.py", "unreachable.py")]
        results = evaluate_properties(self.root, cases)
        self.assertEqual([r["passed"] for r in results], [True, False, False])
        self.assertEqual(results, evaluate_properties(self.root, cases))
        for result in results:
            self.assertEqual(set(result), {"name", "passed", "status", "failure", "digest"})
            self.assertEqual(len(result["digest"]), 64)
            self.assertNotIn(str(self.root), str(result))

    def test_expected_values_mutation_and_fresh_processes(self):
        cases = [dict(name="value", file="good.py", symbol="check", args=[3], kwargs={}, expected=6),
                 dict(name="mutation", file="mutate.py", symbol="check", args=[[1]], kwargs={}, expected=2, unchanged_args=True)]
        state = dict(name="state", file="state.py", symbol="check", args=[0], kwargs={}, expected=1)
        results = evaluate_properties(self.root, cases + [state, state])
        self.assertEqual([r["passed"] for r in results], [True, False, True, True])
        self.assertIn("mutated", results[1]["failure"])

    def test_import_timeout_and_start_failures(self):
        for name in ("broken.py", "slow.py"):
            result = evaluate_properties(self.root, [self.case(file=name)], timeout_seconds=0.1)[0]
            self.assertEqual(result["status"], "environment_failure")
        with patch("cdavc.properties.subprocess.run", side_effect=OSError("secret path")):
            result = evaluate_properties(self.root, [self.case()])[0]
        self.assertEqual(result["status"], "environment_failure")
        self.assertNotIn("secret", result["failure"])

    def test_roundtrip_is_deeply_immutable(self):
        raw = self.case(args=[{"nested": [1]}])
        case = PropertyCase.from_dict(raw)
        raw["args"][0]["nested"].append(2)
        self.assertEqual(case.to_dict()["args"], [{"nested": [1]}])
        output = case.to_dict()
        output["args"].clear()
        self.assertEqual(len(case.to_dict()["args"]), 1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            case.name = "changed"

    def test_invalid_specs_and_timeouts(self):
        invalid = [dict(expected=1), dict(raises="not_an_exception"), dict(file="../bad.py"),
                   dict(file="/bad.py"), dict(file="bad.txt"), dict(file="a\\b.py"),
                   dict(symbol="f()"), dict(symbol="a.class"), dict(args=(1,)),
                   dict(kwargs={1: 2}), dict(args=[float("nan")]), dict(unchanged_args=1),
                   dict(extra=True), dict(name=""), dict(raises=None)]
        for update in invalid:
            with self.subTest(update=update), self.assertRaises(ValueError):
                PropertyCase.from_dict(self.case(**update))
        raw = self.case()
        del raw["raises"]
        with self.assertRaises(ValueError):
            PropertyCase.from_dict(raw)
        for timeout in (0, -1, True, float("inf"), "1"):
            with self.assertRaises(ValueError):
                evaluate_properties(self.root, [], timeout_seconds=timeout)

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "outside.py"
            outside.write_text("def check(x): raise ValueError()")
            (self.root / "link.py").symlink_to(outside)
            with self.assertRaises(ValueError):
                evaluate_properties(self.root, [self.case(file="link.py")])

    def test_src_packages_and_sibling_modules(self):
        package = self.root / "src" / "demo"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "helper.py").write_text("VALUE = 8\n")
        (package / "api.py").write_text("from .helper import VALUE\nclass API:\n    @staticmethod\n    def run(*, x): return x + VALUE\n")
        case = dict(name="package", file="src/demo/api.py", symbol="API.run", args=[], kwargs={"x": 2}, expected=10)
        self.assertTrue(evaluate_properties(self.root, [case])[0]["passed"])
