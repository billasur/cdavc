"""Hidden evaluator for task_h10_convert_timestamp. Usage: python hidden_tests.py [solution_path] (default: solution_stub.py)."""

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
    eq(m.convert_timestamp("2026-10-20T23:30:00-05:00", "Z"), "2026-10-21T04:30:00+00:00")
    eq(m.convert_timestamp("2026-12-31T20:00:00-04:00", "+00:00"), "2027-01-01T00:00:00+00:00")
    eq(m.convert_timestamp("2024-03-01T01:00:00+05:45", "-08:00"), "2024-02-29T11:15:00-08:00")  # leap day backward
    eq(m.convert_timestamp("2026-03-01T01:00:00+05:45", "-08:00"), "2026-02-28T11:15:00-08:00")
    eq(m.convert_timestamp("2026-10-20T00:00:00+00:00", "+05:45"), "2026-10-20T05:45:00+05:45")
    eq(m.convert_timestamp("2026-10-20T10:00:00+09:00", "+09:00"), "2026-10-20T10:00:00+09:00")
    eq(m.convert_timestamp("2026-10-20T10:00:00Z", "Z"), "2026-10-20T10:00:00+00:00")
    eq(m.convert_timestamp("2026-10-20T10:00:00-00:00", "+00:00"), "2026-10-20T10:00:00+00:00")
    for bad_ts in ["2026-10-20T10:00:00", "2026-10-20 10:00:00Z", "2026-13-20T10:00:00Z", "2026-10-20T25:00:00Z", "", "2026-10-20T10:00:00+24:00", "2026-10-20T10:00:00+0530"]:
        raises(ValueError, m.convert_timestamp, bad_ts, "Z")
    for bad_off in ["", "+5:30", "UTC", "+24:00", "+05:60"]:
        raises(ValueError, m.convert_timestamp, "2026-10-20T10:00:00Z", bad_off)


if __name__ == "__main__":
    raise SystemExit(run("hidden", check))
