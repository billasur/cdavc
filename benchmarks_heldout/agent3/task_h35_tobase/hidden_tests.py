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
    assert _eq(m.to_base(0, 2), "0") and _eq(m.to_base(-255, 16), "-ff") and _eq(m.to_base(35, 36), "z") and _eq(m.to_base(36, 36), "10") and _eq(m.to_base(10, 2), "1010") and _eq(m.to_base(-1, 2), "-1") and _eq(m.to_base(2**100, 2), "1" + "0" * 100) and _eq(m.to_base(123456789, 10), "123456789") and _raises(ValueError, m.to_base, 5, 1) and _raises(ValueError, m.to_base, 5, 37)


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
