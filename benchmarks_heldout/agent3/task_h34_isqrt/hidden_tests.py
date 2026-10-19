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
    assert _eq(m.integer_sqrt(0), 0) and _eq(m.integer_sqrt(1), 1) and _eq(m.integer_sqrt(3), 1) and _eq(m.integer_sqrt(4), 2) and _eq(m.integer_sqrt(10**60), 10**30) and _eq(m.integer_sqrt(10**60 - 1), 10**30 - 1) and _eq(m.integer_sqrt((10**25 + 7) ** 2), 10**25 + 7) and _eq(m.integer_sqrt((10**25 + 7) ** 2 - 1), 10**25 + 6) and _eq(m.integer_sqrt(2**53 + 1), 94906265) and _raises(ValueError, m.integer_sqrt, -1)


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
