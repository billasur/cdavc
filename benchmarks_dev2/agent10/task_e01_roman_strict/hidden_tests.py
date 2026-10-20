"""Hidden checks for task_e01_roman_strict (dev2 set, written without reading any held-out test)."""

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
    _eq(m.to_roman(1994), "MCMXCIV")
    _eq(m.to_roman(3999), "MMMCMXCIX")
    _eq(m.to_roman(444), "CDXLIV")
    for n in range(1, 4000):
        _eq(m.from_roman(m.to_roman(n)), n)
    for bad in (0, 4000, -5):
        _raises(ValueError, m.to_roman, bad)
    for bad in (True, 3.0, "5", None):
        _raises(TypeError, m.to_roman, bad)
    for bad in ("IIII", "VX", "IC", "MMMM", "", "iv", " IV", "IV ", "IIX", "XIIII", "VV", "IL", "XM", "ABC"):
        _raises(ValueError, m.from_roman, bad)
    _raises(TypeError, m.from_roman, 5)
    _raises(TypeError, m.from_roman, None)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e01_roman_strict: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
