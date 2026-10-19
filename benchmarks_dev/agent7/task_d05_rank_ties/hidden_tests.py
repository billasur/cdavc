"""Dev-set hidden checks for task_d05_rank_ties. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d05_rank_ties_{path.stem}", path)
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
    _eq(m.rank([90, 80, 80, 70]), [1, 2, 2, 4])
    _eq(m.rank([90, 80, 80, 70], "dense"), [1, 2, 2, 3])
    _eq(m.rank([90, 80, 80, 70], "average"), [1.0, 2.5, 2.5, 4.0])
    _eq(m.rank([5, 5, 5]), [1, 1, 1])
    _eq(m.rank([5, 5, 5], "dense"), [1, 1, 1])
    _eq(m.rank([5, 5, 5], "average"), [2.0, 2.0, 2.0])
    _eq(m.rank([1, 2, 2, 2, 3], "min"), [5, 2, 2, 2, 1])
    _eq(m.rank([1, 2, 2, 2, 3], "average"), [5.0, 3.0, 3.0, 3.0, 1.0])
    _eq(m.rank([1, 2, 2, 2, 3], "dense"), [3, 2, 2, 2, 1])
    _eq(m.rank([2, 2.0, 1]), [1, 1, 3])
    _eq(m.rank([-1, 0, -1]), [2, 1, 2])
    _eq(m.rank(iter([3, 1])), [1, 2])
    r = m.rank([7, 7], "average")
    assert all(type(x) is float for x in r), r
    assert all(type(x) is int for x in m.rank([7, 7])), "min must return ints"
    assert all(type(x) is int for x in m.rank([7, 8], "dense")), "dense must return ints"
    src = [3, 1, 2]
    m.rank(src)
    _eq(src, [3, 1, 2])
    _raises(ValueError, m.rank, [1, 2], "max")
    _raises(ValueError, m.rank, [], "bogus")
    _raises(ValueError, m.rank, [1.0, float("nan")])


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d05_rank_ties: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
