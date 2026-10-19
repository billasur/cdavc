"""Held-out scoring check. Never include in a model prompt.

Usage: python hidden_tests.py [path/to/solution.py]  (default: solution.py beside this file)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path):
    spec = importlib.util.spec_from_file_location("cdavc_heldout_solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"
    return True


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return True
    raise AssertionError(f"expected {error.__name__}")


def check(m):
    assert _eq(m.solve_congruences([]), (0, 1)) and _eq(m.solve_congruences([(1, 4), (3, 6)]), (9, 12)) and _eq(m.solve_congruences([(1, 4), (2, 6)]), None) and _eq(m.solve_congruences([(-1, 5), (12, 7)]), (19, 35)) and _eq(m.solve_congruences([(5, 1)]), (0, 1)) and _eq(m.solve_congruences([(0, 6), (0, 4)]), (0, 12)) and _eq(m.solve_congruences([(7, 10), (7, 10)]), (7, 10)) and _eq(m.solve_congruences([(1, 2), (0, 2)]), None) and _eq(m.solve_congruences([(3, 8), (7, 12), (1, 5)]), (91, 120)) and _raises(ValueError, m.solve_congruences, [(1, 0)])


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else HERE / "solution.py"
    try:
        m = _load(path)
        check(m)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {__file__}: {exc!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
