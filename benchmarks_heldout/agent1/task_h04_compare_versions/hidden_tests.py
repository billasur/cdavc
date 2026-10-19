"""Held-out checks for task_h04_compare_versions (strings/parsing held-out set)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_h04_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    _eq(m.compare_versions("1.0.1", "1.0"), 1)
    _eq(m.compare_versions("10.0", "9.9"), 1)
    _eq(m.compare_versions("1.02", "1.2"), 0)
    _eq(m.compare_versions("1.2.0.0", "1.2"), 0)
    _eq(m.compare_versions("0.0.1", "0.0.0"), 1)
    _eq(m.compare_versions("3", "3"), 0)
    _raises(ValueError, m.compare_versions, "", "1")
    _raises(ValueError, m.compare_versions, "1..2", "1.2")
    _raises(ValueError, m.compare_versions, "1.2.", "1.2")
    _raises(ValueError, m.compare_versions, ".1", "1")
    _raises(ValueError, m.compare_versions, "1.a", "1.0")
    _raises(ValueError, m.compare_versions, "1. 2", "1.2")
    _raises(ValueError, m.compare_versions, "-1.2", "1.2")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_h04_compare_versions: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
