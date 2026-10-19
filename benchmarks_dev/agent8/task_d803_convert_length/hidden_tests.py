"""Dev-set hidden checks for task_d803_convert_length. Probes the spec's invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d803_{path.stem}", path)
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
    f = m.convert_length
    _eq(f(0, "m", "km"), 0.0)
    _eq(f(1500, "m", "km"), 1.5)
    _eq(f(1, "in", "mm"), 25.4)
    _eq(f(10, "mm", "in"), 0.393701)
    _eq(f(2, "KM", "cm"), 200000.0)
    _eq(f(2.5, "m", "m"), 2.5)
    _raises(TypeError, f, "5", "m", "cm")
    _raises(TypeError, f, True, "m", "cm")
    _raises(TypeError, f, 5, 3, "cm")
    _raises(ValueError, f, 5, "yard", "cm")
    _raises(ValueError, f, 5, "m", "")
    _raises(ValueError, f, float("nan"), "m", "cm")
    _raises(ValueError, f, float("inf"), "m", "cm")
    _raises(ValueError, f, -0.5, "m", "cm")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d803_convert_length: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
