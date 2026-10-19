"""Dev-set hidden checks for task_d802_parse_host_port. Probes the spec's invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d802_{path.stem}", path)
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
    f = m.parse_host_port
    _raises(TypeError, f, None)
    _raises(TypeError, f, 8080)
    _raises(ValueError, f, "")
    _raises(ValueError, f, "   ")
    _raises(ValueError, f, "no-colon")
    _raises(ValueError, f, "a:b:80")
    _raises(ValueError, f, ":80")
    _raises(ValueError, f, "host:")
    _raises(ValueError, f, "host:abc")
    _raises(ValueError, f, "host:+80")
    _raises(ValueError, f, "host:8.0")
    _raises(ValueError, f, "host:-1")
    _raises(ValueError, f, "host:0")
    _raises(ValueError, f, "host:65536")
    _eq(f("h:00080"), ("h", 80))
    _eq(f("h:1"), ("h", 1))
    _eq(f("h:65535"), ("h", 65535))
    _eq(f("my.host-name_1:22"), ("my.host-name_1", 22))


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d802_parse_host_port: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
