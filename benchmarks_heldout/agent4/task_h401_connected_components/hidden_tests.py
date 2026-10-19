"""Held-out scoring checks for task_h401_connected_components.

Do not add this module to a model prompt. The benchmark runner invokes
it only as an evaluator after a candidate has been produced.

Run with no arguments to evaluate solution_stub.py next to this file, or pass
a solution path explicitly:
    python hidden_tests.py path/to/solution.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "solution_stub.py"
    spec = importlib.util.spec_from_file_location("cdavc_task_h401_connected_components_candidate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load candidate from {path}")
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


def main() -> int:
    module = _load()
    try:
        _eq(module.connected_components({}), 0)
        _eq(module.connected_components({"a": ["b"], "c": ["d"]}), 2)
        _eq(module.connected_components({"x": ["x"]}), 1)
        _eq(module.connected_components({"a": ["b", "b"], "b": ["a"]}), 1)
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_h401_connected_components: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
