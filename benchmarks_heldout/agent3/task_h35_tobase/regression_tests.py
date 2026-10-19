"""Regression gate.

Usage: python regression_tests.py [path/to/solution.py]  (default: solution.py beside this file)
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
    assert _eq(m.to_base(8, 8), "10") and _eq(m.to_base(7, 8), "7") and all(int(m.to_base(k, 7), 7) == k for k in range(-50, 500))


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
