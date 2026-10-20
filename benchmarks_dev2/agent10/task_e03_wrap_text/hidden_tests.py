"""Hidden checks for task_e03_wrap_text (dev2 set, written without reading any held-out test)."""

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
    f = m.wrap_text
    _eq(f("aaa bbb ccc", 7), ["aaa bbb", "ccc"])
    _eq(f("a  b\tc", 3), ["a b", "c"])
    _eq(f("one two\n\nthree", 7), ["one two", "", "three"])
    _eq(f("a\n  \nb", 5), ["a", "", "b"])
    _eq(f("a\n\n\n\nb", 5), ["a", "", "b"])
    _eq(f("\n\nhello\n\n", 10), ["hello"])
    _eq(f("abcdefghij", 4), ["abcd", "efgh", "ij"])
    _eq(f("abcdefgh", 4), ["abcd", "efgh"])
    _eq(f("ab abcdefghij c", 4), ["ab", "abcd", "efgh", "ij c"])
    _eq(f("a b", 1), ["a", "b"])
    _eq(f("ab cd", 5), ["ab cd"])
    _eq(f("ab cd", 4), ["ab", "cd"])
    _eq(f("line one\nline two", 20), ["line one line two"])
    _eq(f("", 5), [])
    _eq(f("  \n ", 5), [])
    _raises(ValueError, f, "x", 0)
    _raises(ValueError, f, "x", -1)
    _raises(TypeError, f, "x", 2.0)
    _raises(TypeError, f, "x", True)
    _raises(TypeError, f, None, 5)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e03_wrap_text: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
