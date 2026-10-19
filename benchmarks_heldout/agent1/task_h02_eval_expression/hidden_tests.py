"""Hidden checks for task_h02_eval_expression (strings/parsing held-out set)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_h02_{path.stem}", path)
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
    _eq(m.eval_expression("8-3-2"), 3)
    _eq(m.eval_expression("16/4/2"), 2)
    _eq(m.eval_expression("10/4"), 2.5)
    _eq(m.eval_expression("-3+5"), 2)
    _eq(m.eval_expression("2*-3"), -6)
    _eq(m.eval_expression("3--2"), 5)
    _eq(m.eval_expression(" 12  /  3 "), 4)
    _eq(m.eval_expression("((7))"), 7)
    _eq(type(m.eval_expression("10/5")), int)
    _eq(type(m.eval_expression("10/4")), float)
    _raises(ValueError, m.eval_expression, "")
    _raises(ValueError, m.eval_expression, "   ")
    _raises(ValueError, m.eval_expression, "2+")
    _raises(ValueError, m.eval_expression, "(1+2")
    _raises(ValueError, m.eval_expression, "1+2)")
    _raises(ValueError, m.eval_expression, "abc")
    _raises(ValueError, m.eval_expression, "1/0")
    _raises(ValueError, m.eval_expression, "2(3)")
    _raises(ValueError, m.eval_expression, "1 2")


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_h02_eval_expression: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
