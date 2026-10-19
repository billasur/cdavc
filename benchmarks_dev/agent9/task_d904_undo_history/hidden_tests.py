"""Held-out checks for task_d904_undo_history. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d904_{path.stem}", path)
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
    _eq(m.new_history(), {"past": [], "future": []})
    hist = m.new_history()
    _eq(m.undo(hist), None)
    _eq(m.redo(hist), None)
    _eq(m.current(hist), None)
    _eq(hist, {"past": [], "future": []})
    m.push(hist, 1)
    m.push(hist, 2)
    m.push(hist, 3)
    _eq(m.undo(hist), 3)
    _eq(m.undo(hist), 2)
    _eq(m.current(hist), 1)
    _eq(m.redo(hist), 2)
    _eq(m.current(hist), 2)
    m.push(hist, 4)
    _eq(m.redo(hist), None)
    _eq(m.current(hist), 4)
    _eq(m.undo(hist), 4)
    _eq(m.undo(hist), 2)
    _eq(m.undo(hist), 1)
    _eq(m.undo(hist), None)
    _eq(m.current(hist), None)
    _eq(m.redo(hist), 1)
    _eq(m.redo(hist), 2)
    _eq(m.redo(hist), 4)
    _eq(m.redo(hist), None)
    _eq(m.current(hist), 4)
    none_hist = m.new_history()
    m.push(none_hist, None)
    _eq(m.current(none_hist), None)
    _eq(len(none_hist["past"]), 1)
    _eq(m.undo(none_hist), None)
    _eq(none_hist, {"past": [], "future": [None]})
    _raises(TypeError, m.push, "nope", 1)
    _raises(TypeError, m.undo, {})
    _raises(TypeError, m.redo, {"past": []})
    _raises(TypeError, m.current, {"past": [], "future": "x"})
    _raises(TypeError, m.push, ["past", "future"], 1)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d904_undo_history: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
