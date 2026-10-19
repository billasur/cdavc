"""Held-out checks for task_h05_parse_log_line (strings/parsing held-out set)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_h05_{path.stem}", path)
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
    _eq(
        m.parse_log_line("2026-10-20 23:59:59 [ERROR] disk /dev/sda [sdb] full"),
        {"date": "2026-10-20", "time": "23:59:59", "level": "ERROR", "message": "disk /dev/sda [sdb] full"},
    )
    _eq(
        m.parse_log_line("  2026-01-01 00:00:00 [DEBUG] boot  "),
        {"date": "2026-01-01", "time": "00:00:00", "level": "DEBUG", "message": "boot"},
    )
    _raises(ValueError, m.parse_log_line, "2026-13-01 00:00:00 [INFO] x")
    _raises(ValueError, m.parse_log_line, "2026-02-30 00:00:00 [INFO] x")
    _raises(ValueError, m.parse_log_line, "2026-1-1 02:03:04 [INFO] x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 24:00:00 [INFO] x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 02:60:00 [INFO] x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 02:30:00 [TRACE] x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 02:30:00 [info] x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 02:30:00 INFO x")
    _raises(ValueError, m.parse_log_line, "2026-10-20 02:30:00 [INFO]")
    _raises(ValueError, m.parse_log_line, "2026-10-20  02:30:00 [INFO] x")
    _raises(ValueError, m.parse_log_line, "")
    _raises(ValueError, m.parse_log_line, "not a log line at all")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_h05_parse_log_line: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
