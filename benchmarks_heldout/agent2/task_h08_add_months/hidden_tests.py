"""Hidden evaluator for task_h08_add_months. Usage: python hidden_tests.py [solution_path] (default: solution_stub.py)."""

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
    eq(m.add_months("2024-01-31", 1), "2024-02-29")
    eq(m.add_months("2100-01-31", 1), "2100-02-28")  # 2100 is not a leap year
    eq(m.add_months("2000-01-31", 1), "2000-02-29")  # 2000 is
    eq(m.add_months("2026-03-31", -1), "2026-02-28")
    eq(m.add_months("2026-01-10", -1), "2025-12-10")
    eq(m.add_months("2026-12-31", 2), "2027-02-28")
    eq(m.add_months("2026-05-31", 13), "2027-06-30")
    eq(m.add_months("2026-05-31", -29), "2023-12-31")
    eq(m.add_months("2026-05-31", 0), "2026-05-31")
    eq(m.add_months("0099-01-31", 1), "0099-02-28")
    raises(ValueError, m.add_months, "2026-02-30", 1)
    raises(ValueError, m.add_months, "not-a-date", 1)


if __name__ == "__main__":
    raise SystemExit(run("hidden", check))
