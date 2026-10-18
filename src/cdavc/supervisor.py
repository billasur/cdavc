"""Deterministic task runner for the CD-AVC v1 workflow."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import ast
import tempfile
from pathlib import Path
from typing import Any

from .graph import Task, TaskGraph
from .providers import Provider, ProviderUnavailableError


class VerificationFailure(RuntimeError):
    """A candidate failed one of the deterministic gates."""


class Supervisor:
    def __init__(self, graph_path: Path, provider: Provider, *, timeout_seconds: int = 30) -> None:
        self.graph_path = graph_path.resolve()
        self.root = self.graph_path.parent
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.graph = TaskGraph.from_dict(json.loads(self.graph_path.read_text()))
        self.execution_root = self.root

    def run(self) -> dict[str, Any]:
        completed: set[str] = set()
        results: dict[str, Any] = {}
        with tempfile.TemporaryDirectory(prefix="cdavc-") as workspace:
            self.execution_root = Path(workspace) / self.root.name
            shutil.copytree(
                self.root,
                self.execution_root,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", ".venv", ".cache", "__pycache__", "execution_log.json", "execution_report.md"),
            )
            while len(completed) < len(self.graph.tasks):
                runnable = [task for task in self.graph.runnable_tasks(completed) if task.id not in results]
                if not runnable:
                    raise RuntimeError("no runnable tasks remain; graph state is inconsistent")
                task = runnable[0]
                result = self._run_task(task)
                results[task.id] = result
                if result["status"] == "COMPLETED":
                    self._sync_task_files(task)
                    completed.add(task.id)
                else:
                    break
        self.execution_root = self.root
        output = {"project_id": self.graph.project_id, "tasks": results}
        (self.root / "execution_log.json").write_text(json.dumps(output, indent=2) + "\n")
        (self.root / "execution_report.md").write_text(render_report(output))
        return output

    def _run_task(self, task: Task) -> dict[str, Any]:
        missing_tests = [path for path in task.test_files if not (self.execution_root / path).is_file()]
        if not task.test_files:
            return {
                "status": "FAILED",
                "attempts": 0,
                "attempt_log": [],
                "failure": f"{task.id}: at least one declared test file is required",
            }
        if missing_tests:
            return {
                "status": "FAILED",
                "attempts": 0,
                "attempt_log": [],
                "failure": f"{task.id}: declared test file does not exist: {missing_tests[0]}",
            }
        original = {path: _read_optional(self.execution_root / path) for path in task.implementation_files}
        attempts: list[dict[str, Any]] = []
        previous_failure = ""
        for attempt in range(1, task.max_retries + 2):
            prompt = self._prompt(task, previous_failure)
            try:
                response = self.provider.complete([{"role": "user", "content": prompt}])
                self._apply_response(task, response)
                self._verify(task)
            except (ValueError, VerificationFailure, ProviderUnavailableError, OSError, subprocess.SubprocessError) as exc:
                self._restore(original)
                previous_failure = str(exc)
                attempts.append({"attempt": attempt, "status": "REJECTED", "failure": previous_failure})
                continue
            attempts.append({"attempt": attempt, "status": "ACCEPTED"})
            return {"status": "COMPLETED", "attempts": attempt, "attempt_log": attempts, "failure": ""}
        return {"status": "FAILED", "attempts": len(attempts), "attempt_log": attempts, "failure": previous_failure}

    def _prompt(self, task: Task, previous_failure: str) -> str:
        failure = f"\nPrevious deterministic failure:\n{previous_failure}\n" if previous_failure else ""
        return (
            f"Implement task {task.id}: {task.title}.\n"
            f"Allowed implementation files: {', '.join(task.implementation_files)}\n"
            f"Required symbols: {', '.join(task.symbols) or '(none)'}\n"
            f"Invariants: {', '.join(task.invariants) or '(see tests)'}\n"
            "Return only JSON in the form {\"files\": {\"path\": \"complete file contents\"}}. "
            "Never modify test files.\n" + failure
        )

    def _apply_response(self, task: Task, response: str) -> None:
        try:
            payload = json.loads(response)
            files = payload["files"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("provider response must be JSON with a files object") from exc
        if not isinstance(files, dict) or not files:
            raise ValueError("provider files must be a non-empty object")
        allowed = set(task.implementation_files)
        if not set(files).issubset(allowed):
            raise ValueError("provider changed a file outside the allowed implementation files")
        for relative, content in files.items():
            if not isinstance(relative, str) or not isinstance(content, str):
                raise ValueError("provider file paths and contents must be strings")
            workspace_root = self.execution_root.resolve()
            target = (workspace_root / relative).resolve()
            if workspace_root not in target.parents:
                raise ValueError("provider attempted a path outside the project")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    def _verify(self, task: Task) -> None:
        for relative in task.implementation_files:
            source = (self.execution_root / relative).read_text()
            try:
                tree = compile(source, relative, "exec", ast.PyCF_ONLY_AST)
            except SyntaxError as exc:
                raise VerificationFailure(f"AST gate failed: {relative}:{exc.lineno}: {exc.msg}") from exc
            declared = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            missing = set(task.symbols) - declared
            if missing:
                raise VerificationFailure(f"AST gate failed: missing symbols {sorted(missing)}")
        self._run_command(task.test_command, "targeted test")
        if task.negative_test_command:
            self._run_command(task.negative_test_command, "negative test")
        self._run_command(("python", "-m", "unittest", "discover", "-s", "tests"), "regression test")

    def _run_command(self, command: tuple[str, ...], label: str) -> None:
        if command[0] in {"python", "python3"}:
            command = (sys.executable, *command[1:])
        env = dict(os.environ)
        env["PYTHONPATH"] = str(self.execution_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
        try:
            result = subprocess.run(command, cwd=self.execution_root, env=env, capture_output=True, text=True, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise VerificationFailure(f"{label} timed out after {self.timeout_seconds}s") from exc
        if result.returncode:
            output = (result.stdout + "\n" + result.stderr).replace(str(self.execution_root), "$WORKSPACE").replace(str(self.root), "$PROJECT_ROOT").strip()[-2000:]
            raise VerificationFailure(f"{label} failed:\n{output}")

    def _restore(self, original: dict[str, str | None]) -> None:
        for relative, content in original.items():
            target = self.execution_root / relative
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_text(content)

    def _sync_task_files(self, task: Task) -> None:
        for relative in task.implementation_files:
            source = self.execution_root / relative
            destination = self.root / relative
            if not source.is_file():
                raise VerificationFailure(f"verified implementation file is missing: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".cdavc-tmp")
            shutil.copyfile(source, temporary)
            temporary.replace(destination)


def _read_optional(path: Path) -> str | None:
    return path.read_text() if path.exists() else None


def render_report(result: dict[str, Any]) -> str:
    lines = [f"# CD-AVC execution report\n", f"Project: `{result['project_id']}`\n", "| Task | Status | Attempts |", "|---|---:|---:|"]
    for task_id, task in result["tasks"].items():
        lines.append(f"| `{task_id}` | {task['status']} | {task['attempts']} |")
        for attempt in task.get("attempt_log", []):
            if attempt.get("failure"):
                lines.append(f"\n- Attempt {attempt['attempt']} rejected: `{attempt['failure']}`")
    return "\n".join(lines) + "\n"
