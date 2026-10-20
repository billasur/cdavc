"""Hidden checks for task_e05_brace_expand (dev2 set, written without reading any held-out test)."""

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
    f = m.expand_braces
    _eq(f("a{b,c}d"), ["abd", "acd"])
    _eq(f("{a,b{c,d}}"), ["a", "bc", "bd"])
    _eq(f("{a,b}{1,2}"), ["a1", "a2", "b1", "b2"])
    _eq(f("x{,y}"), ["x", "xy"])
    _eq(f("{a}"), ["{a}"])
    _eq(f("{}"), ["{}"])
    _eq(f("{x{1,2}}"), ["{x1}", "{x2}"])
    _eq(f("{{a,b}}"), ["{a}", "{b}"])
    _eq(f(r"\{a,b\}"), ["{a,b}"])
    _eq(f(r"{a\,b,c}"), ["a,b", "c"])
    _eq(f(r"\\{a,b}"), ["\\a", "\\b"])
    _eq(f("{a,b"), ["{a,b"])
    _eq(f("a}b"), ["a}b"])
    _eq(f(""), [""])
    _eq(f("plain"), ["plain"])
    _eq(f("{a,a}"), ["a", "a"])
    _eq(f("{a,b}c{d,e}"), ["acd", "ace", "bcd", "bce"])
    _eq(f("{,}"), ["", ""])
    _eq(f("{a,{b,c}}"), ["a", "b", "c"])
    _raises(TypeError, f, None)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e05_brace_expand: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
