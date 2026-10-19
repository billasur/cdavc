"""Dev-set hidden checks for task_d03_sliding_windows. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d03_sliding_windows_{path.stem}", path)
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
    _eq(m.windows([1, 2, 3, 4, 5], 2, 2, keep_partial=True), [[1, 2], [3, 4], [5]])
    _eq(m.windows([1, 2, 3, 4, 5], 3, 3), [[1, 2, 3]])
    _eq(m.windows([1, 2, 3, 4, 5], 3, 3, keep_partial=True), [[1, 2, 3], [4, 5]])
    _eq(m.windows([1, 2, 3, 4], 3, 1, keep_partial=True), [[1, 2, 3], [2, 3, 4]])
    _eq(m.windows([1, 2, 3, 4, 5], 2, 3), [[1, 2], [4, 5]])
    _eq(m.windows([1, 2, 3, 4, 5, 6], 2, 3), [[1, 2], [4, 5]])
    _eq(m.windows([1, 2, 3, 4, 5, 6], 2, 3, keep_partial=True), [[1, 2], [4, 5]])
    _eq(m.windows([1, 2, 3, 4, 5, 6, 7], 2, 3, keep_partial=True), [[1, 2], [4, 5], [7]])
    _eq(m.windows([1, 2], 5), [])
    _eq(m.windows([1, 2], 5, keep_partial=True), [[1, 2]])
    _eq(m.windows([], 2, keep_partial=True), [])
    _eq(m.windows([1, 2, 3], 3), [[1, 2, 3]])
    _eq(m.windows([1, 2, 3], 3, keep_partial=True), [[1, 2, 3]])
    _eq(m.windows([1, 2, 3], 1, 2), [[1], [3]])
    _eq(m.windows("abcde", 2, 2, keep_partial=True), [["a", "b"], ["c", "d"], ["e"]])
    _eq(m.windows((1, 2, 3), 2), [[1, 2], [2, 3]])
    _raises(ValueError, m.windows, [1, 2], 0)
    _raises(ValueError, m.windows, [1, 2], 2, 0)
    _raises(ValueError, m.windows, [], 0)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d03_sliding_windows: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
