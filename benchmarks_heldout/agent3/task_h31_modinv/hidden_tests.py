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
    assert _eq(m.mod_inverse(-3, 7), 2) and _eq(m.mod_inverse(10, 7), 5) and _eq(m.mod_inverse(1, 2), 1) and _eq(m.mod_inverse(7, 40), 23) and _eq((12345678901234567 * m.mod_inverse(12345678901234567, 1000000007)) % 1000000007, 1) and _raises(ValueError, m.mod_inverse, 4, 8) and _raises(ValueError, m.mod_inverse, 0, 5) and _raises(ValueError, m.mod_inverse, 3, 1) and _raises(ValueError, m.mod_inverse, 3, 0) and _raises(ValueError, m.mod_inverse, 6, 9)


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
