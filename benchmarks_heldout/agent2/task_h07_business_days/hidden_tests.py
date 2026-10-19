"""Hidden evaluator for task_h07_business_days. Usage: python hidden_tests.py [solution_path] (default: solution_stub.py)."""

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
    eq(m.business_days("2026-10-19", "2026-10-19"), 0)
    eq(m.business_days("2026-10-17", "2026-10-19"), 0)  # Sat, Sun
    eq(m.business_days("2026-10-16", "2026-10-19"), 1)  # Fri only, Monday excluded
    eq(m.business_days("2026-10-19", "2026-10-26", ["2026-10-21"]), 4)
    eq(m.business_days("2026-10-19", "2026-10-26", ["2026-10-21", "2026-10-21"]), 4)
    eq(m.business_days("2026-10-19", "2026-10-26", ["2026-10-24", "2026-12-25"]), 5)
    eq(m.business_days("2026-10-19", "2026-10-26", ["2026-10-26"]), 5)  # end day not counted
    eq(m.business_days("2026-01-01", "2027-01-01"), 261)
    eq(m.business_days("2024-02-26", "2024-03-04"), 5)  # leap day Thursday 29th
    raises(ValueError, m.business_days, "2026-10-20", "2026-10-19")
    raises(ValueError, m.business_days, "2026-02-30", "2026-03-05")
    raises(ValueError, m.business_days, "2026-10-19", "2026-10-26", ["bad"])


if __name__ == "__main__":
    raise SystemExit(run("hidden", check))
