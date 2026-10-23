"""Deterministic task runner for the CD-AVC v1 workflow."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from .graph import Task, TaskGraph
from .invariants import has_raise_statement, required_exception
from .payloads import parse_payload
from .providers import Provider
from .redact import redact_paths
from .accounting import Budget, BudgetExceeded, UsageLedger, complete_recorded
from .edits import apply_candidate
from .verification import ArtifactStore, VerificationContract, WorkspaceSnapshot, candidate_payload, verify_workspace
from .providers import ProviderUnavailableError
from .context import ContextSession, is_context_request


Event = Callable[[str], None]
DEFAULT_TEST_COMMAND = ("python", "-m", "unittest", "discover", "-s", "tests")
_MAX_PROMPT_FILE_CHARS = 6000
# Matches the benchmark's candidate cap so `cdavc run` and the measured `cdavc`
# arm hand a repair draw the same repair context.
_MAX_CANDIDATE_CHARS = 4000
_EMPTY_TEST_RUN = re.compile(r"\bRan 0 tests\b|\bno tests ran\b", re.IGNORECASE)
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


class VerificationFailure(RuntimeError):
    """A candidate failed one of the deterministic gates."""


# Failures whose rejected candidate is worth quoting for the next draw. Measured
# self-repair results: syntax/name/traceable-exception errors repair well with the
# candidate in context, while assertion failures (logic the tests disagree with)
# repair at coin-flip rates and benefit from a fresh derivation instead.
_CONCRETE_ERROR = re.compile(
    r"SyntaxError|IndentationError|TabError|NameError|ImportError|ModuleNotFoundError|"
    r"TypeError|AttributeError|IndexError|KeyError|ZeroDivisionError",
    re.IGNORECASE,
)
_LOGIC_FAILURE = re.compile(r"AssertionError|FAILED \(", re.IGNORECASE)
_TRACEABLE_FAILURE = re.compile(
    r"must be JSON|syntax|could not start|timed out|" + _CONCRETE_ERROR.pattern,
    re.IGNORECASE,
)


def _is_repairable(failure: str) -> bool:
    text = failure or ""
    if _LOGIC_FAILURE.search(text):
        # A concrete exception name outranks the surrounding failed-test verdict;
        # a bare assertion outcome means the logic itself is wrong.
        return bool(_CONCRETE_ERROR.search(text))
    return bool(_TRACEABLE_FAILURE.search(text))


def _split_env_prefix(command: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], dict[str, str]]:
    """Peel leading NAME=value words so a pasted shell line keeps its environment."""
    words = list(command)
    overrides: dict[str, str] = {}
    while words and _ENV_ASSIGNMENT.match(words[0]):
        name, _, value = words.pop(0).partition("=")
        overrides[name] = value
    if not words:
        raise VerificationFailure(f"command only sets environment variables: {' '.join(command)}")
    return tuple(words), overrides


class Supervisor:
    def __init__(
        self,
        graph_path: Path | None,
        provider: Provider,
        *,
        timeout_seconds: float = 120,
        root: Path | None = None,
        graph: TaskGraph | None = None,
        dry_run: bool = False,
        on_event: Event | None = None,
        samples: int = 1,
        budget: Budget | None = None,
        context_budget_chars: int = 12000,
        max_context_requests: int = 2,
    ) -> None:
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
            raise ValueError("samples must be a whole number of at least 1")
        if graph is None:
            if graph_path is None:
                raise ValueError("a task graph or a graph path is required")
            self.graph_path: Path | None = Path(graph_path).resolve()
            self.graph = TaskGraph.from_dict(json.loads(self.graph_path.read_text()))
            base = self.graph_path.parent
        else:
            self.graph_path = None
            self.graph = graph
            base = Path.cwd()
        self.root = (Path(root) if root is not None else base).resolve()
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run
        self.on_event = on_event
        self.samples = samples
        self.execution_root = self.root
        self.budget = budget or Budget()
        self.artifacts = ArtifactStore(self.root / ".cdavc" / "artifacts")
        self._active_snapshot: WorkspaceSnapshot | None = None
        self._last_evidence: dict[str, Any] | None = None
        self._task_original: dict[str, str | None] = {}
        if isinstance(context_budget_chars, bool) or not isinstance(context_budget_chars, int) or context_budget_chars < 512:
            raise ValueError("context_budget_chars must be at least 512")
        if isinstance(max_context_requests, bool) or not isinstance(max_context_requests, int) or max_context_requests < 0:
            raise ValueError("max_context_requests must be nonnegative")
        self.context_budget_chars = context_budget_chars
        self.max_context_requests = max_context_requests

    def run(self) -> dict[str, Any]:
        completed: set[str] = set()
        results: dict[str, Any] = {}
        snapshot = WorkspaceSnapshot.capture(self.root)
        with snapshot.materialize() as workspace:
            self.execution_root = workspace
            while len(completed) < len(self.graph.tasks):
                runnable = [task for task in self.graph.runnable_tasks(completed) if task.id not in results]
                if not runnable:
                    raise RuntimeError("no runnable tasks remain; graph state is inconsistent")
                task = runnable[0]
                result = self._run_task(task)
                results[task.id] = result
                if result["status"] == "COMPLETED":
                    if not self.dry_run:
                        self._sync_task_files(task)
                    completed.add(task.id)
                else:
                    break
        self.execution_root = self.root
        output = {"project_id": self.graph.project_id, "tasks": results}
        (self.root / "execution_log.json").write_text(json.dumps(output, indent=2) + "\n")
        (self.root / "execution_report.md").write_text(render_report(output))
        patch = render_patch(output)
        if patch:
            (self.root / "execution_patch.diff").write_text(patch)
        return output

    def _run_task(self, task: Task) -> dict[str, Any]:
        missing_tests = [path for path in task.test_files if not (self.execution_root / path).is_file()]
        if not task.test_files:
            return self._failed(task, "at least one declared test file is required")
        if missing_tests:
            return self._failed(task, f"declared test file does not exist: {missing_tests[0]}")
        parent = self.execution_root
        snapshot = WorkspaceSnapshot.capture(parent)
        original = {path: _read_optional(parent / path) for path in task.implementation_files}
        self._task_original = original
        self._active_snapshot = snapshot
        ledger = UsageLedger(self.budget)
        attempts: list[dict[str, Any]] = []
        previous_failure = ""
        previous_candidate = ""
        seen_replies: set[str] = set()
        # ``samples`` raises the floor on candidate draws without overriding the task's
        # own retry budget: each draw is an independent sample, and every draw after the
        # first is told why the one before it was rejected.
        total = max(task.max_retries + 1, self.samples)
        for attempt in range(1, total + 1):
            self._emit(f"task {task.id}: request {attempt}/{total}")
            with snapshot.materialize() as workspace:
                self.execution_root = workspace
                self._last_evidence = None
                session = self._context_session(task)
                context = session.initial()
                prompt = self._prompt(task, previous_failure, candidate=previous_candidate, context=context)
                try:
                    response = self._request_candidate(prompt, context, session, ledger)
                    reply_digest = hashlib.sha256(response.text.encode("utf-8")).hexdigest()
                    if reply_digest in seen_replies:
                        # An identical reply cannot fix the rejection it already produced;
                        # spending the remaining draws on it is waste, not evidence.
                        previous_failure = (f"candidate stagnation: request {attempt} returned the exact reply "
                                            f"already rejected by an earlier request; stopping early instead of "
                                            "spending the remaining draw budget")
                        attempts.append({"attempt": attempt, "status": "REJECTED", "failure": previous_failure,
                                         "verification_evidence": self._last_evidence, "stagnation": True})
                        self._emit(f"task {task.id}: {previous_failure}")
                        self.execution_root = parent
                        result = self._failed(task, previous_failure, attempts)
                        result["outcome"] = "stagnation"
                        return self._accounted(result, ledger)
                    seen_replies.add(reply_digest)
                    self._apply_response(task, response.text)
                    evidence = self._verify(task)
                    self._reject_unchanged(task, workspace, original)
                    ledger.check()
                except ProviderUnavailableError:
                    self.artifacts.put({"task_id": task.id, "accounting": ledger.summary(), "call_log": ledger.entries})
                    self.execution_root = parent
                    raise
                except (ValueError, VerificationFailure, OSError, subprocess.SubprocessError) as exc:
                    quoted = _candidate_context(workspace, task.implementation_files, original)
                    # Repair literature: traceable syntax/exception failures repair well when
                    # the rejected candidate is quoted; assertion/logic failures repair at
                    # coin-flip rates, and a fresh derivation informed by the failure does better.
                    previous_candidate = quoted if _is_repairable(str(exc)) else ""
                    previous_failure = str(exc)
                    attempts.append({"attempt": attempt, "status": "REJECTED", "failure": previous_failure,
                                     "verification_evidence": self._last_evidence})
                    self._emit(f"task {task.id}: request {attempt}/{total} rejected: {_first_line(previous_failure)}")
                    self.execution_root = parent
                    outcome = exc.outcome if isinstance(exc, BudgetExceeded) else (self._last_evidence or {}).get("outcome")
                    if outcome in {"budget_exhausted", "inconclusive", "environment_failure"}:
                        result = self._failed(task, previous_failure, attempts)
                        result["outcome"] = outcome
                        if self._last_evidence is not None:
                            # The CLI must expose the same evidence object the
                            # benchmark records for the identical failure.
                            result["verification_evidence"] = self._last_evidence
                        return self._accounted(result, ledger)
                    continue
                attempts.append({"attempt": attempt, "status": "ACCEPTED", "verification_evidence": evidence})
                selected = candidate_payload(workspace, VerificationContract.from_task(task))
                result = {"status": "COMPLETED", "attempts": len(attempts), "attempt_log": attempts, "failure": "",
                          "outcome": evidence["outcome"], "verification_evidence": evidence,
                          "artifact_digest": evidence["artifact_digest"]}
                diff = self._diff(task, original)
                if diff:
                    result["diff"] = diff
            self.execution_root = parent
            apply_candidate(parent, task.implementation_files, selected)
            self._emit(f"task {task.id}: verified after {attempt} request(s)")
            return self._accounted(result, ledger)
        self.execution_root = parent
        result = self._failed(task, previous_failure, attempts)
        result["verification_evidence"] = self._last_evidence
        result["outcome"] = "rejected_with_counterexample"
        return self._accounted(result, ledger)

    def _reject_unchanged(self, task: Task, workspace: Path, original: dict[str, str | None]) -> None:
        """A candidate identical to the original proves the checks discriminate nothing.

        If the declared gates accept a byte-unchanged project, accepting the task
        would be a no-op ablation failure: the tests pass with or without the
        requested change. Reject the draw with that reason so the next draw must
        produce an actual change the checks can witness.
        """
        changed = any(_read_optional(workspace / path) != content for path, content in original.items())
        if not changed:
            raise VerificationFailure(
                "candidate left every implementation file byte-identical to the original; the declared "
                "checks accepted the unchanged project, so they do not discriminate this task — produce "
                "the requested change")

    def _accounted(self, result: dict[str, Any], ledger: UsageLedger) -> dict[str, Any]:
        result["accounting"] = ledger.summary()
        result["call_log"] = list(ledger.entries)
        result["usage_digest"] = self.artifacts.put({"accounting": result["accounting"], "call_log": result["call_log"]})
        return result

    def _failed(self, task: Task, failure: str, attempts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        self._emit(f"task {task.id}: failed: {_first_line(failure)}")
        return {"status": "FAILED", "attempts": len(attempts or []), "attempt_log": attempts or [], "failure": failure}

    def _request_candidate(self, prompt: str, context: str, session: ContextSession, ledger: UsageLedger):
        completion = complete_recorded(self.provider, [{"role": "user", "content": prompt}], ledger)
        if completion.metadata.get("finish_reason") == "length":
            # A truncated reply cannot contain a complete candidate; say how to fix it
            # instead of letting JSON parsing report a generic syntax error.
            raise ValueError("completion was truncated at the provider's token limit before a full "
                             "candidate was produced; raise the provider's context/output limit")
        for request in range(self.max_context_requests + 1):
            try:
                payload = parse_payload(completion.text)
            except ValueError:
                return completion
            if not is_context_request(payload):
                return completion
            if request == self.max_context_requests:
                raise BudgetExceeded("context request budget exhausted")
            retrieved = session.respond(payload)
            completion = complete_recorded(self.provider,
                [{"role": "user", "content": prompt.replace(context, retrieved, 1)}], ledger, purpose="context_retrieval")
        raise AssertionError("unreachable context loop")

    def _context_session(self, task: Task) -> ContextSession:
        paths = tuple(dict.fromkeys((*task.test_files, *task.implementation_files, *task.context_files)))
        paths = tuple(path for path in paths if (self.execution_root / path).is_file())
        roles = {path: "test" if path in task.test_files else "current" for path in paths}
        return ContextSession(self.execution_root, paths, query=" ".join((task.title, *task.symbols, *task.invariants)),
                              max_chars=self.context_budget_chars, roles=roles)

    def _prompt(self, task: Task, previous_failure: str, *, candidate: str = "", context: str | None = None) -> str:
        failure = f"\nPrevious deterministic failure:\n{previous_failure}\n" if previous_failure else ""
        previous_candidate = (
            f"\nPrevious candidate, which failed the gates below; repair it instead of starting over:\n{candidate}\n"
            if candidate
            else ""
        )
        sections = [
            f"Implement task {task.id}: {task.title}.\n"
            f"Allowed implementation files: {', '.join(task.implementation_files)}\n"
            f"Required symbols: {', '.join(task.symbols) or '(none)'}\n"
            f"Invariants: {', '.join(task.invariants) or '(see tests)'}\n"
            "The test files below define done. Never modify a test file.\n"
        ]
        sections.append(context if context is not None else self._context_session(task).initial())
        sections.append(previous_candidate)
        sections.append(
            "\nReturn only JSON, in one of these two forms:\n"
            '{"files": {"path/to/file.py": "complete file contents"}}\n'
            '{"edits": [{"file": "path/to/file.py", "find": "exact existing text", "replace": "new text"}]}\n'
            "Use edits for a small change inside a large file; each find string must match exactly once. "
            "Use repository-relative paths only and do not wrap the JSON in markdown.\n" + failure
        )
        return "".join(sections)

    def _excerpt(self, relative: str) -> str:
        content = (self.execution_root / relative).read_text()
        if len(content) <= _MAX_PROMPT_FILE_CHARS:
            return content
        return content[:_MAX_PROMPT_FILE_CHARS] + f"\n... truncated after {_MAX_PROMPT_FILE_CHARS} characters ...\n"

    def _apply_response(self, task: Task, response: str) -> None:
        try:
            payload = parse_payload(response)
        except ValueError as exc:
            raise ValueError("provider response must be JSON with a files object or an edits list") from exc
        if not isinstance(payload, dict):
            raise ValueError("provider response must be a JSON object")
        try:
            apply_candidate(self.execution_root, task.implementation_files, payload)
        except ValueError as exc:
            if "unknown implementation" in str(exc):
                raise ValueError("provider changed a file outside the allowed implementation files") from exc
            raise

    def _apply_edit(self, edit: Any, allowed: set[str]) -> None:
        apply_candidate(self.execution_root, tuple(allowed), {"edits": [edit]})

    def _target(self, relative: str) -> Path:
        workspace_root = self.execution_root.resolve()
        target = (workspace_root / relative).resolve()
        if workspace_root not in target.parents:
            raise ValueError("provider attempted a path outside the project")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _verify(self, task: Task) -> dict[str, Any]:
        evidence = verify_workspace(self.execution_root, VerificationContract.from_task(task),
                                    snapshot=self._active_snapshot, store=self.artifacts,
                                    timeout_seconds=self.timeout_seconds)
        self._last_evidence = evidence
        if not evidence["accepted"]:
            prefix = "AST gate failed: " if evidence["failure"].lower().startswith("ast") else ""
            raise VerificationFailure(prefix + evidence["failure"])
        return evidence

    def _run_command(self, command: tuple[str, ...], label: str, *, reject_empty_tests: bool = False) -> None:
        command, overrides = _split_env_prefix(command)
        if command[0] in {"python", "python3"}:
            command = (sys.executable, *command[1:])
        env = dict(os.environ)
        env.update(overrides)
        source_root = self.execution_root / "src"
        if source_root.is_dir():
            env["PYTHONPATH"] = str(source_root) + os.pathsep + env.get("PYTHONPATH", "")
        # A rewrite that keeps the file size within the same second would otherwise reuse stale bytecode.
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            result = subprocess.run(command, cwd=self.execution_root, env=env, capture_output=True, text=True, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise VerificationFailure(f"{label} timed out after {self.timeout_seconds}s") from exc
        output = redact_paths(result.stdout + "\n" + result.stderr, self.execution_root, self.root).strip()
        if result.returncode:
            raise VerificationFailure(f"{label} failed:\n{output[-2000:]}")
        if reject_empty_tests and _EMPTY_TEST_RUN.search(output):
            flag = "--test-command" if label == "targeted test" else "--regression"
            key = "test_command" if label == "targeted test" else "regression_command"
            raise VerificationFailure(
                f"{label} ran no tests, so it verified nothing. Give {flag} (or {key} in a task graph) the command "
                f"that runs this project's tests, for example 'python -m pytest -q' or 'npm test'."
            )

    def _restore(self, original: dict[str, str | None]) -> None:
        for relative, content in original.items():
            target = self.execution_root / relative
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_text(content)

    def _sync_task_files(self, task: Task) -> None:
        for relative, original in self._task_original.items():
            if _read_optional(self.root / relative) != original:
                raise VerificationFailure(f"project changed during verification: {relative}")
        payload = candidate_payload(self.execution_root, VerificationContract.from_task(task))
        apply_candidate(self.root, task.implementation_files, payload)

    def _diff(self, task: Task, original: dict[str, str | None]) -> str:
        chunks: list[str] = []
        for relative, before in original.items():
            after = _read_optional(self.execution_root / relative)
            if before == after:
                continue
            chunks.extend(
                difflib.unified_diff(
                    _diff_lines(before),
                    _diff_lines(after),
                    fromfile="/dev/null" if before is None else f"a/{relative}",
                    tofile=f"b/{relative}",
                )
            )
        return "".join(chunks)

    def _emit(self, message: str) -> None:
        if self.on_event is not None:
            self.on_event(message)


def _candidate_context(root: Path, implementation_files: tuple[str, ...], original: dict[str, str | None]) -> str:
    """Quote the files a rejected candidate changed, so the next draw can repair them."""
    parts: list[str] = []
    for relative in implementation_files:
        try:
            content = (root / relative).read_bytes().decode("utf-8")
        except OSError:
            continue
        if content == (original.get(relative) or ""):
            continue
        if len(content) > _MAX_CANDIDATE_CHARS:
            content = content[:_MAX_CANDIDATE_CHARS] + f"\n... truncated after {_MAX_CANDIDATE_CHARS} characters ...\n"
        parts.append(f"--- {relative} ---\n{content}")
    return "\n".join(parts)


def _read_optional(path: Path) -> str | None:
    return path.read_bytes().decode("utf-8") if path.exists() else None


def _diff_lines(content: str | None) -> list[str]:
    if not content:
        return []
    lines = content.splitlines(keepends=True)
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def _first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else "task failed"


def render_patch(result: dict[str, Any]) -> str:
    return "".join(task.get("diff", "") for task in result["tasks"].values())


def render_report(result: dict[str, Any]) -> str:
    lines = [f"# CD-AVC execution report\n", f"Project: `{result['project_id']}`\n",
             "| Task | Status | Outcome | Attempts | Provider calls | Usage |", "|---|---|---|---:|---:|---|"]
    for task_id, task in result["tasks"].items():
        accounting = task.get("accounting", {})
        usage = "complete" if accounting.get("usage_complete") else "incomplete" if accounting else "not recorded"
        lines.append(f"| `{task_id}` | {task['status']} | {task.get('outcome', 'not evaluated')} | "
                     f"{task['attempts']} | {accounting.get('calls', '—')} | {usage} |")
        if accounting and not accounting.get("usage_complete"):
            lines.append("\nUsage is incomplete: known counters are lower bounds, not a zero-cost or fully metered total.")
        evidence = task.get("verification_evidence")
        if evidence:
            lines.append(f"\nEvidence SHA-256: `{evidence['evidence_digest']}`; artifact: `{evidence['artifact_digest']}`.")
        for attempt in task.get("attempt_log", []):
            if attempt.get("failure"):
                lines.append(f"\n- Attempt {attempt['attempt']} rejected: `{attempt['failure']}`")
    return "\n".join(lines) + "\n"
