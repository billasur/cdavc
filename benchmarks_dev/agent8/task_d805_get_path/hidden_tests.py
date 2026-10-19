"""Dev-set hidden checks for task_d805_get_path. Probes the spec's invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d805_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    f = m.get_path
    _eq(f({"a": None}, "a"), None)
    _eq(f({}, "x", None), None)
    _eq(f({"a": {"b": []}}, "a.b"), [])
    _eq(f({"a": 1}, "b.c", "fallback"), "fallback")
    _raises(KeyError, f, {"a": 1}, "b")
    _raises(KeyError, f, {"a": {"b": 1}}, "a.c")
    _raises(TypeError, f, {"a": 5}, "a.b")
    _raises(TypeError, f, [1], "a")
    _raises(TypeError, f, {"a": 1}, None)
    _raises(ValueError, f, {"a": 1}, "")
    _raises(ValueError, f, {"a": 1}, ".a")
    _raises(ValueError, f, {"a": 1}, "a.")
    _raises(ValueError, f, {"a": {"b": 1}}, "a..b")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d805_get_path: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
