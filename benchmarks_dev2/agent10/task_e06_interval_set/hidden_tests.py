"""Hidden checks for task_e06_interval_set (dev2 set, written without reading any held-out test)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_{path.stem}", path)
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
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"expected {error.__name__}, got {type(exc).__name__}: {exc}")
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    S = m.IntervalSet
    s = S(); s.add(1, 3); s.add(3, 5)
    _eq(s.intervals(), [(1, 5)])
    s = S(); s.add(5, 7); s.add(1, 3)
    _eq(s.intervals(), [(1, 3), (5, 7)])
    s = S(); s.add(1, 10); s.remove(4, 6)
    _eq(s.intervals(), [(1, 4), (6, 10)])
    s.remove(10, 12); s.remove(0, 1)
    _eq(s.intervals(), [(1, 4), (6, 10)])
    s.remove(0, 100)
    _eq(s.intervals(), [])
    s = S(); s.add(1, 2); s.add(4, 5); s.add(7, 8); s.add(2, 7)
    _eq(s.intervals(), [(1, 8)])
    s = S(); s.add(1, 2); s.add(5, 6); s.add(3, 4)
    _eq(s.intervals(), [(1, 2), (3, 4), (5, 6)])
    s = S(); s.add(0, 0)
    _eq(s.intervals(), [])
    s = S(); s.add(1, 3)
    _eq((s.contains(0), s.contains(1), s.contains(2), s.contains(3)), (False, True, True, False))
    s = S(); s.add(-5, -2)
    _eq((s.contains(-5), s.contains(-2), s.total()), (True, False, 3))
    s = S(); s.add(1, 10); s.remove(1, 4)
    _eq(s.intervals(), [(4, 10)])
    s.remove(8, 10)
    _eq(s.intervals(), [(4, 8)])
    got = s.intervals(); got.append((99, 100))
    _eq(s.intervals(), [(4, 8)])
    _eq(s.add(1, 2), None)
    _eq(s.remove(1, 2), None)
    _raises(ValueError, s.add, 3, 1)
    _raises(ValueError, s.remove, 3, 1)
    _raises(TypeError, s.add, 1.0, 2)
    _raises(TypeError, s.add, True, 2)
    _raises(TypeError, s.contains, "1")
    _raises(TypeError, s.contains, True)
    s = S(); s.add(1, 5); s.add(2, 3)
    _eq((s.intervals(), s.total()), ([(1, 5)], 4))


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e06_interval_set: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
