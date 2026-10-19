"""Held-out checks for task_d903_kv_record_codec. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d903_{path.stem}", path)
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
    _eq(m.dump_record({}), "")
    _eq(m.parse_record(""), {})
    _eq(m.dump_record({"b": "1", "a": "2"}), "a=2;b=1")
    _eq(m.dump_record({"x": "a=b;c%d"}), "x=a%3Db%3Bc%25d")
    _eq(m.parse_record("x=a%3Db%3Bc%25d"), {"x": "a=b;c%d"})
    _eq(m.parse_record("k=%253B"), {"k": "%3B"})
    _eq(m.dump_record({"k": "%3B"}), "k=%253B")
    _eq(m.parse_record("=v"), {"": "v"})
    _eq(m.parse_record("k="), {"k": ""})
    _eq(m.parse_record("a=b=c"), {"a": "b=c"})
    _eq(m.parse_record("sp ace=va l"), {"sp ace": "va l"})
    for record in [{"a=b": "x;y%z"}, {"": ""}, {"café": "naïve"}, {"1": "2", "10": "x", "2": "y"}]:
        _eq(m.parse_record(m.dump_record(record)), record)
    _raises(ValueError, m.parse_record, "a=1;b")
    _raises(ValueError, m.parse_record, "a=1%")
    _raises(ValueError, m.parse_record, "a=1%2")
    _raises(ValueError, m.parse_record, "a=1%zz")
    _raises(ValueError, m.parse_record, "a=1%3d")
    _raises(ValueError, m.parse_record, "a=1;a=2")
    _raises(ValueError, m.parse_record, "a=1;%61=2")
    _raises(TypeError, m.dump_record, ["a=1"])
    _raises(TypeError, m.dump_record, {1: "x"})
    _raises(TypeError, m.dump_record, {"a": 1})
    _raises(TypeError, m.parse_record, None)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d903_kv_record_codec: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
