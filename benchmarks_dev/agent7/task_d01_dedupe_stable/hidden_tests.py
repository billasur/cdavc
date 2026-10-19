"""Dev-set hidden checks for task_d01_dedupe_stable. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d01_dedupe_stable_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    _eq(m.dedupe([]), [])
    _eq(m.dedupe([1, True, 1.0, 2, 2.0]), [1, 2])
    _eq(m.dedupe([None, 0, None, False]), [None, 0])
    _eq(m.dedupe(["Apple", "apple", "BANANA", "Banana", "cherry"], key=str.lower), ["Apple", "BANANA", "cherry"])
    _eq(m.dedupe((x for x in "mississippi")), ["m", "i", "s", "p"])
    _eq(m.dedupe("aabbA"), ["a", "b", "A"])
    _eq(m.dedupe([(1, "x"), (2, "x"), (3, "y")], key=lambda t: t[1]), [(1, "x"), (3, "y")])
    src = [2, 2, 1]
    _eq(m.dedupe(src), [2, 1])
    _eq(src, [2, 2, 1])
    calls = []
    def k(x):
        calls.append(x)
        return x % 3
    _eq(m.dedupe([1, 4, 2, 5, 3], key=k), [1, 2, 3])
    _eq(calls, [1, 4, 2, 5, 3])


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d01_dedupe_stable: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
