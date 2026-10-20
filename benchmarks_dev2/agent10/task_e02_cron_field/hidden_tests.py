"""Hidden checks for task_e02_cron_field (dev2 set, written without reading any held-out test)."""

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
    f = m.expand_field
    _eq(f("*/15", 0, 59), [0, 15, 30, 45])
    _eq(f("1-5/2", 0, 59), [1, 3, 5])
    _eq(f("5/20", 0, 59), [5, 25, 45])
    _eq(f("1,3,5", 0, 59), [1, 3, 5])
    _eq(f("5,1,5-6", 0, 10), [1, 5, 6])
    _eq(f("*", 1, 3), [1, 2, 3])
    _eq(f("0-6/7", 0, 6), [0])
    _eq(f("3", 0, 6), [3])
    _eq(f("*/1", 1, 3), [1, 2, 3])
    _eq(f("*/100", 0, 59), [0])
    _eq(f("2-4,3-5", 0, 9), [2, 3, 4, 5])
    for bad in ("60", "", ",1", "1,,2", "1,", "*/0", "*/-1", "*/x", "5-1", "a", "1-", "-1", "+1", "1.5", " 1", "1 ", "*/", "1-5/0", "1-2-3", "/5"):
        _raises(ValueError, f, bad, 0, 59)
    _raises(ValueError, f, "0", 1, 12)
    _raises(ValueError, f, "13", 1, 12)
    _raises(TypeError, f, None, 0, 59)
    _raises(TypeError, f, 5, 0, 59)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e02_cron_field: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
