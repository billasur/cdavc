"""Hidden checks for task_e04_osa_distance (dev2 set, written without reading any held-out test)."""

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
    f = m.osa_distance
    _eq(f("", ""), 0)
    _eq(f("abc", ""), 3)
    _eq(f("", "abc"), 3)
    _eq(f("kitten", "sitting"), 3)
    _eq(f("ab", "ba"), 1)
    _eq(f("ca", "abc"), 3)
    _eq(f("abc", "acb"), 1)
    _eq(f("a", "b"), 1)
    _eq(f("flaw", "lawn"), 2)
    _eq(f("same", "same"), 0)
    _eq(f("ab", "a"), 1)
    _eq(f("kitten", "sitting", 3), 3)
    _eq(f("kitten", "sitting", 2), 3)
    _eq(f("abc", "xyz", 0), 1)
    _eq(f("a", "a", 0), 0)
    _eq(f("abcd", "", 1), 2)
    _raises(TypeError, f, 1, "a")
    _raises(TypeError, f, "a", None)
    _raises(ValueError, f, "a", "b", -1)
    _raises(TypeError, f, "a", "b", 1.5)
    _raises(TypeError, f, "a", "b", True)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e04_osa_distance: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
