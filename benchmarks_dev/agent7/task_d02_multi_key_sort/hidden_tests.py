"""Dev-set hidden checks for task_d02_multi_key_sort. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d02_multi_key_sort_{path.stem}", path)
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
    r = [
        {"id": 1, "g": "x", "s": 5},
        {"id": 2, "g": "y", "s": 5},
        {"id": 3, "g": "x", "s": 5},
        {"id": 4, "g": "y", "s": 9},
    ]
    ids = lambda rows: [x["id"] for x in rows]
    _eq(ids(m.sort_records(r, [("s", False)])), [1, 2, 3, 4])
    _eq(ids(m.sort_records(r, [("s", True)])), [4, 1, 2, 3])
    _eq(ids(m.sort_records(r, [("g", False), ("s", True)])), [1, 3, 4, 2])
    _eq(ids(m.sort_records(r, [("g", True), ("id", True)])), [4, 2, 3, 1])
    miss = [{"id": 1}, {"id": 2, "v": 3}, {"id": 3}, {"id": 4, "v": 1}]
    _eq(ids(m.sort_records(miss, [("v", False)])), [4, 2, 1, 3])
    _eq(ids(m.sort_records(miss, [("v", True)])), [2, 4, 1, 3])
    miss2 = [{"id": 1, "w": 2}, {"id": 2, "w": 1}, {"id": 3, "v": 0, "w": 9}]
    _eq(ids(m.sort_records(miss2, [("v", False), ("w", False)])), [3, 2, 1])
    _eq(ids(m.sort_records(miss2, [("v", True), ("w", True)])), [3, 1, 2])
    _eq(ids(m.sort_records([{"id": 1, "v": 0}, {"id": 2}, {"id": 3, "v": -1}], [("v", False)])), [3, 1, 2])
    src = [{"id": 2, "v": 2}, {"id": 1, "v": 1}]
    snap = [dict(x) for x in src]
    out = m.sort_records(src, [("v", False)])
    assert out is not src
    _eq(src, snap)
    c = m.sort_records(src, [])
    _eq(c, snap)
    assert c is not src


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d02_multi_key_sort: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
