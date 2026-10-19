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
    assert _eq(m.prime_factorization(2), [(2, 1)]) and _eq(m.prime_factorization(97), [(97, 1)]) and _eq(m.prime_factorization(1024), [(2, 10)]) and _eq(m.prime_factorization(999999000001), [(999999000001, 1)]) and _eq(m.prime_factorization(10**12), [(2, 12), (5, 12)]) and _eq(m.prime_factorization(9 * 9 * 49), [(3, 4), (7, 2)]) and _eq(m.prime_factorization(1000003 * 999983), [(999983, 1), (1000003, 1)]) and _raises(ValueError, m.prime_factorization, 1) and _raises(ValueError, m.prime_factorization, 0) and _raises(ValueError, m.prime_factorization, -12)


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
