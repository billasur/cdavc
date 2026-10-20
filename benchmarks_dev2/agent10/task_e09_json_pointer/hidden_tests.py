"""Hidden checks for task_e09_json_pointer (dev2 set, written without reading any held-out test)."""

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
    g, s = m.pointer_get, m.pointer_set
    doc = {"a": {"b": [10, 20]}, "": 5, "a/b": 1, "m~n": 2, "~1": 3, "n": None}
    _eq(g(doc, "/a/b/1"), 20)
    _eq(g(doc, ""), doc)
    _eq(g(doc, "/"), 5)
    _eq(g(doc, "/a~1b"), 1)
    _eq(g(doc, "/m~0n"), 2)
    _eq(g(doc, "/~01"), 3)
    _eq(g(doc, "/n"), None)
    _eq(g([[1]], "/0/0"), 1)
    for bad in ("a", "/~2", "/~", "x"):
        _raises(ValueError, g, doc, bad)
    for bad in ("/a/b/01", "/a/b/+1", "/a/b/-1", "/a/b/x", "/a/b/-"):
        _raises(ValueError, g, doc, bad)
    _raises(IndexError, g, doc, "/a/b/5")
    _raises(KeyError, g, doc, "/zzz")
    _raises(KeyError, g, doc, "/a/b/0/x")
    _raises(KeyError, g, doc, "/n/x")
    _raises(TypeError, g, doc, 5)
    base = {"a": {"b": [10, 20]}}
    r = s(base, "/a/b/-", 30)
    _eq(r, {"a": {"b": [10, 20, 30]}})
    _eq(base, {"a": {"b": [10, 20]}})
    _eq(s(base, "/a/b/2", 30), {"a": {"b": [10, 20, 30]}})
    _eq(s(base, "/a/b/0", 99), {"a": {"b": [99, 20]}})
    _eq(s(base, "/a/c", 1), {"a": {"b": [10, 20], "c": 1}})
    _eq(s(base, "", {"x": 1}), {"x": 1})
    _raises(IndexError, s, base, "/a/b/3", 1)
    _raises(KeyError, s, base, "/q/r", 1)
    _raises(ValueError, s, base, "/a/b/01", 1)
    _raises(TypeError, s, base, None, 1)
    val = {"k": [1]}
    out = s({}, "/v", val)
    val["k"].append(2)
    _eq(out, {"v": {"k": [1]}})
    _eq(base, {"a": {"b": [10, 20]}})


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e09_json_pointer: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
