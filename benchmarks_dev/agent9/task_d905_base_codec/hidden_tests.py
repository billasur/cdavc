"""Held-out checks for task_d905_base_codec. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d905_{path.stem}", path)
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
    _eq(m.to_base(0, 2), "0")
    _eq(m.to_base(0, 36), "0")
    _eq(m.to_base(255, 16), "ff")
    _eq(m.to_base(35, 36), "z")
    _eq(m.to_base(36, 36), "10")
    _eq(m.to_base(123456789, 36), "21i3v9")
    _eq(m.from_base("FF", 16), 255)
    _eq(m.from_base(" z ", 36), 35)
    _eq(m.from_base("007", 10), 7)
    _eq(m.from_base("0", 2), 0)
    _eq(m.from_base("21I3V9", 36), 123456789)
    for n in [0, 1, 2, 35, 36, 37, 255, 4096, 999983]:
        for b in [2, 8, 10, 16, 36]:
            _eq(m.from_base(m.to_base(n, b), b), n)
    _raises(ValueError, m.from_base, "2", 2)
    _raises(ValueError, m.from_base, "z", 35)
    _raises(ValueError, m.from_base, "", 10)
    _raises(ValueError, m.from_base, "   ", 10)
    _raises(ValueError, m.from_base, "+7", 10)
    _raises(ValueError, m.from_base, "-7", 10)
    _raises(ValueError, m.from_base, "1_0", 10)
    _raises(ValueError, m.to_base, -1, 2)
    _raises(ValueError, m.to_base, 5, 1)
    _raises(ValueError, m.to_base, 5, 37)
    _raises(ValueError, m.from_base, "10", 0)
    _raises(TypeError, m.to_base, True, 2)
    _raises(TypeError, m.to_base, 5, True)
    _raises(TypeError, m.to_base, 5.0, 2)
    _raises(TypeError, m.to_base, "5", 2)
    _raises(TypeError, m.from_base, 42, 10)
    _raises(TypeError, m.from_base, "10", "2")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d905_base_codec: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
