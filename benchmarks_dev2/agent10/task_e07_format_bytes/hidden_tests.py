"""Hidden checks for task_e07_format_bytes (dev2 set, written without reading any held-out test)."""

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
    f = m.format_bytes
    _eq(f(0), "0 B")
    _eq(f(999), "999 B")
    _eq(f(1000), "1.0 kB")
    _eq(f(1500), "1.5 kB")
    _eq(f(1050), "1.1 kB")
    _eq(f(1049), "1.0 kB")
    _eq(f(999949), "999.9 kB")
    _eq(f(999950), "1.0 MB")
    _eq(f(5 * 10**6), "5.0 MB")
    _eq(f(1023, binary=True), "1023 B")
    _eq(f(1024, binary=True), "1.0 KiB")
    _eq(f(1536, binary=True), "1.5 KiB")
    _eq(f(1048575, binary=True), "1.0 MiB")
    _eq(f(10**19), "10000.0 PB")
    _raises(ValueError, f, -1)
    _raises(TypeError, f, 1.5)
    _raises(TypeError, f, True)
    _raises(TypeError, f, "1")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e07_format_bytes: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
