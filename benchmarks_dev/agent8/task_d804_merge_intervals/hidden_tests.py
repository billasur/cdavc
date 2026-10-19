"""Dev-set hidden checks for task_d804_merge_intervals. Probes the spec's invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d804_{path.stem}", path)
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
    f = m.merge_intervals
    _eq(f([[2, 3], [1, 2]]), [[1, 3]])
    _eq(f([[1, 10], [2, 3], [4, 5]]), [[1, 10]])
    _eq(f([(1, 2), (3, 4)]), [[1, 2], [3, 4]])
    _eq(f([[5, 5]]), [[5, 5]])
    _eq(f([[-3, -1], [0, 0], [1, 2.5]]), [[-3, -1], [0, 0], [1, 2.5]])
    _eq(f([[1.5, 2.5], [2.5, 4]]), [[1.5, 4]])
    _raises(TypeError, f, "1-2")
    _raises(TypeError, f, [[1, 2, 3]])
    _raises(TypeError, f, [5])
    _raises(TypeError, f, [[True, 2]])
    _raises(TypeError, f, [["1", 2]])
    _raises(ValueError, f, [[3, 1]])
    _raises(ValueError, f, [[float("nan"), 1]])
    _raises(ValueError, f, [[1, float("inf")]])


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d804_merge_intervals: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
