"""Hidden evaluator for task_h06_iso_duration. Usage: python hidden_tests.py [solution_path] (default: solution_stub.py)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load(path=None):
    """Load the solution under test. Default: solution_stub.py next to this file."""
    path = Path(path or (sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("solution_stub.py")))
    spec = importlib.util.spec_from_file_location("solution_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def raises(error, function, *args):
    try:
        function(*args)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run(kind, check):
    try:
        check(load())
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"{kind} test failed: {exc}", file=sys.stderr)
        return 1
    return 0


def check(m):
    eq(m.parse_duration("P2W"), 1209600.0)
    eq(m.parse_duration("PT0.5S"), 0.5)
    eq(m.parse_duration("P1W1DT1H1M1S"), 604800 + 86400 + 3661.0)
    eq(m.parse_duration("PT36H"), 129600.0)
    eq(type(m.parse_duration("PT1S")), float)
    for bad in ["", "P", "PT", "P1D T1H", "1D", "P1Y", "P1M", "P1DT", "PT1H1D", "PT1.5M", "P1.5D", "PT-5S", "pt5s", "PT1S1S", "PT1M1H"]:
        raises(ValueError, m.parse_duration, bad)


if __name__ == "__main__":
    raise SystemExit(run("hidden", check))
