"""Hidden checks for task_e13_parse_query (dev2 set, written without reading any held-out test)."""

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
    f = m.parse_query
    _eq(f("a=1&b=2"), {"a": "1", "b": "2"})
    _eq(f("?a=1"), {"a": "1"})
    _eq(f("??a=1"), {"?a": "1"})
    _eq(f("a=1&&b=2&"), {"a": "1", "b": "2"})
    _eq(f("flag"), {"flag": ""})
    _eq(f("a=b=c"), {"a": "b=c"})
    _eq(f("a=1&a=2&a=3"), {"a": ["1", "2", "3"]})
    _eq(f("x[]=1"), {"x": ["1"]})
    _eq(f("x[]=1&x[]=2"), {"x": ["1", "2"]})
    _eq(f("x=1&x[]=2"), {"x": ["1", "2"]})
    _eq(f("x[]=1&x=2"), {"x": ["1", "2"]})
    _eq(f("q=a+b"), {"q": "a b"})
    _eq(f("q=a%2Bb"), {"q": "a+b"})
    _eq(f("q=%41%42"), {"q": "AB"})
    _eq(f("q=%zz"), {"q": "%zz"})
    _eq(f("q=100%"), {"q": "100%"})
    _eq(f("q=%E4"), {"q": "\ufffd"})
    _eq(f("%E2%82%AC=eur"), {"\u20ac": "eur"})
    _eq(f("=v&k=1"), {"k": "1"})
    _eq(f("[]=1&k=2"), {"k": "2"})
    _eq(f("a="), {"a": ""})
    _eq(f(""), {})
    _eq(list(f("z=1&a=2&m=3")), ["z", "a", "m"])
    _eq(f("a+b=c+d"), {"a b": "c d"})
    _raises(TypeError, f, None)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e13_parse_query: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
