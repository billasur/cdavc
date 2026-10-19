"""Dev-set hidden checks for task_d04_merge_intervals. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d04_merge_intervals_{path.stem}", path)
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
    _eq(m.merge_intervals([(1, 3), (3, 5)]), [(1, 5)])
    _eq(m.merge_intervals([(8, 10), (1, 3), (2, 6)]), [(1, 6), (8, 10)])
    _eq(m.merge_intervals([(1, 10), (2, 3), (4, 5)]), [(1, 10)])
    _eq(m.merge_intervals([(1, 2), (3, 4)]), [(1, 2), (3, 4)])
    _eq(m.merge_intervals([(2, 2)]), [])
    _eq(m.merge_intervals([(1, 5), (3, 3), (7, 7)]), [(1, 5)])
    _eq(m.merge_intervals([(1, 3), (3, 3), (3, 5)]), [(1, 5)])
    _eq(m.merge_intervals([(5, 6), (1, 5), (0, 1)]), [(0, 6)])
    _eq(m.merge_intervals([(0.5, 1.5), (1.5, 2)]), [(0.5, 2)])
    _eq(m.merge_intervals([(-5, -1), (-3, 2)]), [(-5, 2)])
    _eq(m.merge_intervals(iter([[4, 6], [1, 2]])), [(1, 2), (4, 6)])
    _eq(m.merge_intervals([[1, 3], [2, 4]]), [(1, 4)])
    assert all(type(x) is tuple for x in m.merge_intervals([[1, 3]]))
    src = [(3, 4), (1, 2)]
    m.merge_intervals(src)
    _eq(src, [(3, 4), (1, 2)])
    _raises(ValueError, m.merge_intervals, [(3, 1)])
    _raises(ValueError, m.merge_intervals, [(1, 10), (5, 4)])


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d04_merge_intervals: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
