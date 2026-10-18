"""Validated task graph data structures for the CD-AVC supervisor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


class GraphError(ValueError):
    """Raised when a task graph is malformed or unsafe to execute."""


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    dependencies: tuple[str, ...]
    implementation_files: tuple[str, ...]
    test_files: tuple[str, ...]
    symbols: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    test_command: tuple[str, ...] = ("python", "-m", "unittest", "discover", "-s", "tests")
    negative_test_command: tuple[str, ...] | None = None
    max_retries: int = 2


class TaskGraph:
    def __init__(self, project_id: str, tasks: tuple[Task, ...]) -> None:
        self.project_id = project_id
        self.tasks = tasks
        self._by_id = {task.id: task for task in tasks}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskGraph":
        if not isinstance(payload, dict) or not isinstance(payload.get("project_id"), str) or not payload["project_id"]:
            raise GraphError("project_id must be a string")
        raw_tasks = payload.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise GraphError("tasks must be a non-empty list")

        tasks: list[Task] = []
        seen: set[str] = set()
        for raw in raw_tasks:
            if not isinstance(raw, dict):
                raise GraphError("each task must be an object")
            task_id = raw.get("id")
            title = raw.get("title")
            if not isinstance(task_id, str) or not task_id or task_id in seen:
                raise GraphError(f"invalid or duplicate task id: {task_id!r}")
            if not isinstance(title, str) or not title:
                raise GraphError(f"{task_id}: title must be a non-empty string")
            seen.add(task_id)
            dependencies = _string_tuple(raw.get("dependencies", []), f"{task_id}.dependencies")
            implementation_files = _safe_paths(raw.get("implementation_files"), f"{task_id}.implementation_files")
            test_files = _safe_paths(raw.get("test_files", []), f"{task_id}.test_files")
            symbols = _string_tuple(raw.get("symbols", []), f"{task_id}.symbols")
            invariants = _string_tuple(raw.get("invariants", []), f"{task_id}.invariants")
            test_command = _command_tuple(raw.get("test_command", ["python", "-m", "unittest", "discover", "-s", "tests"]), f"{task_id}.test_command")
            negative = raw.get("negative_test_command")
            negative_command = None if negative is None else _command_tuple(negative, f"{task_id}.negative_test_command")
            max_retries = raw.get("max_retries", 2)
            if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0 or max_retries > 5:
                raise GraphError(f"{task_id}: max_retries must be between 0 and 5")
            tasks.append(Task(task_id, title, dependencies, implementation_files, test_files, symbols, invariants, test_command, negative_command, max_retries))

        graph = cls(payload["project_id"], tuple(tasks))
        graph._validate_dependencies()
        return graph

    def runnable_tasks(self, completed: set[str]) -> list[Task]:
        return [task for task in self.tasks if task.id not in completed and set(task.dependencies) <= completed]

    def task(self, task_id: str) -> Task:
        return self._by_id[task_id]

    def _validate_dependencies(self) -> None:
        ids = set(self._by_id)
        for task in self.tasks:
            unknown = set(task.dependencies) - ids
            if unknown:
                raise GraphError(f"{task.id}: unknown dependencies: {sorted(unknown)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise GraphError("task graph contains a dependency cycle")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in self.task(task_id).dependencies:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task in self.tasks:
            visit(task.id)


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise GraphError(f"{label} must be a list of non-empty strings")
    return tuple(value)


def _safe_paths(value: Any, label: str) -> tuple[str, ...]:
    paths = _string_tuple(value, label)
    for path in paths:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or path == ".":
            raise GraphError(f"{label} contains unsafe path: {path!r}")
    return paths


def _command_tuple(value: Any, label: str) -> tuple[str, ...]:
    command = _string_tuple(value, label)
    if not command:
        raise GraphError(f"{label} cannot be empty")
    return command
