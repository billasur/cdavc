"""Small standard-library helpers for the fixed benchmark evaluators."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parent


def load_solution(task_id: str) -> ModuleType:
    """Load one task solution without importing a package from the task tree."""

    path = ROOT / "tasks" / task_id / "solution.py"
    if not path.is_file():
        raise FileNotFoundError(f"unknown benchmark task: {task_id}")
    spec = importlib.util.spec_from_file_location(f"cdavc_{task_id}_solution", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load solution for {task_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
