"""Dev-set hidden checks for task_d801_normalize_user_record. Probes the spec's invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d801_{path.stem}", path)
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
    f = m.normalize_user_record
    _raises(TypeError, f, ["not a dict"])
    _raises(KeyError, f, {"email": "a@b.co", "age": 1})
    _raises(KeyError, f, {"name": "A", "age": 1})
    _raises(KeyError, f, {"name": "A", "email": "a@b.co"})
    _raises(TypeError, f, {"name": 5, "email": "a@b.co", "age": 1})
    _raises(ValueError, f, {"name": "   ", "email": "a@b.co", "age": 1})
    _raises(ValueError, f, {"name": "A", "email": "plain", "age": 1})
    _raises(ValueError, f, {"name": "A", "email": "a@@b.co", "age": 1})
    _raises(ValueError, f, {"name": "A", "email": "@b.co", "age": 1})
    _raises(ValueError, f, {"name": "A", "email": "a@b", "age": 1})
    _raises(TypeError, f, {"name": "A", "email": "a@b.co", "age": True})
    _raises(ValueError, f, {"name": "A", "email": "a@b.co", "age": -1})
    _raises(ValueError, f, {"name": "A", "email": "a@b.co", "age": 151})
    _eq(
        f({"name": "A", "email": "a@b.co", "age": 0}),
        {"name": "A", "email": "a@b.co", "age": 0, "tags": []},
    )
    _eq(
        f({"name": "A", "email": "a@b.co", "age": 150, "tags": ["b", " a ", "a", "", "b"]}),
        {"name": "A", "email": "a@b.co", "age": 150, "tags": ["b", "a"]},
    )
    _raises(TypeError, f, {"name": "A", "email": "a@b.co", "age": 1, "tags": "abc"})
    _raises(TypeError, f, {"name": "A", "email": "a@b.co", "age": 1, "tags": ["ok", 7]})


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d801_normalize_user_record: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
