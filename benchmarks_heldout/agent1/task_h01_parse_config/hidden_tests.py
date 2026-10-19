"""Held-out checks for task_h01_parse_config. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_h01_{path.stem}", path)
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
    _eq(m.parse_config(""), {})
    _eq(m.parse_config("# only a comment\n; another\n\n"), {})
    _eq(
        m.parse_config("# c\n[s]\nk = v1\nk = v2\n\n[t]\nx = y\n[s]\nz = w"),
        {"s": {"k": "v2", "z": "w"}, "t": {"x": "y"}},
    )
    _eq(m.parse_config("[s]\nquery = a=b&c=d"), {"s": {"query": "a=b&c=d"}})
    _eq(m.parse_config("[s]\nmsg = hello world  # not a comment"), {"s": {"msg": "hello world  # not a comment"}})
    _eq(m.parse_config("  [ padded ]  \n  key  =  value  "), {"padded": {"key": "value"}})
    _raises(ValueError, m.parse_config, "k = v")
    _raises(ValueError, m.parse_config, "[s]\nnotakey")
    _raises(ValueError, m.parse_config, "[s]\n= v")
    _raises(ValueError, m.parse_config, "[unclosed\nk = v")
    _raises(ValueError, m.parse_config, "[]\nk = v")
    _raises(ValueError, m.parse_config, "[  ]\nk = v")
    _raises(ValueError, m.parse_config, "[s] trailing\nk = v")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_h01_parse_config: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
