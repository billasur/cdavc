"""Small standard-library helpers for the fixed benchmark evaluators."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parent


def load_module(task_id: str, name: str) -> ModuleType:
    """Load one module of a task solution without importing a package from the task tree."""

    directory = ROOT / "tasks" / task_id
    path = directory / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"unknown benchmark module: {task_id}/{name}.py")
    spec = importlib.util.spec_from_file_location(f"cdavc_{task_id}_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} for {task_id}")
    module = importlib.util.module_from_spec(spec)
    # A multi-file task imports its sibling modules by bare name, so the task
    # directory has to be importable while the module executes.
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    spec.loader.exec_module(module)
    return module


def load_solution(task_id: str) -> ModuleType:
    """Load the entry module of one task solution."""

    return load_module(task_id, "solution")
