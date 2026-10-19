"""Public checks for task_d801_normalize_user_record (dev set, validation/exception classes)."""

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


def _checks(m):
    _eq(
        m.normalize_user_record(
            {"name": "  Ada  ", "email": "ADA@Example.COM", "age": 30, "tags": ["x", "x", " y "], "extra": 1}
        ),
        {"name": "Ada", "email": "ada@example.com", "age": 30, "tags": ["x", "y"]},
    )


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"public test failed for task_d801_normalize_user_record: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
