"""Hidden checks for task_e11_min_coins (dev2 set, written without reading any held-out test)."""

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
    f = m.min_coins
    _eq(f([1, 3, 4], 6), [3, 3])
    _eq(f([1, 3, 4, 5], 8), [5, 3])
    _eq(f([2], 3), None)
    _eq(f([], 0), [])
    _eq(f([], 5), None)
    _eq(f([5, 1, 5], 10), [5, 5])
    _eq(f([1], 0), [])
    _eq(f([25, 10, 5, 1], 63), [25, 25, 10, 1, 1, 1])
    _eq(f([9, 6, 5, 1], 11), [6, 5])
    _eq(f([3, 7], 11), None)
    _eq(f([7, 3], 10), [7, 3])
    _eq(f((2, 5), 9), [5, 2, 2])
    _raises(ValueError, f, [1, 0], 3)
    _raises(ValueError, f, [1, -2], 3)
    _raises(ValueError, f, [1], -1)
    _raises(TypeError, f, [1, "2"], 3)
    _raises(TypeError, f, [1, True], 3)
    _raises(TypeError, f, [1.0], 3)
    _raises(TypeError, f, "12", 3)
    _raises(TypeError, f, [1], 2.0)
    _raises(TypeError, f, [1], True)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e11_min_coins: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
