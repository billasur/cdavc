"""Shared loader and assertion helper for the dev corpus tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_solution(task_id: str):
    path = ROOT / "benchmarks" / "dev" / "tasks" / task_id / "solution.py"
    spec = importlib.util.spec_from_file_location("cdavc_dev_" + task_id, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    if actual != expected or type(actual) is not type(expected):
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def run(cases, symbols, task_id: str) -> None:
    module = load_solution(task_id)
    function = getattr(module, symbols[task_id])
    for args, expected, raises in cases[task_id]:
        if raises:
            try:
                function(*args)
            except Exception as exc:  # noqa: BLE001 - the test asserts the type
                if type(exc).__name__ != raises:
                    raise AssertionError(
                        f"expected {raises}, got {type(exc).__name__}: {exc}"
                    ) from exc
            else:
                raise AssertionError(f"expected {raises}, no exception raised")
        else:
            _eq(function(*args), expected)
