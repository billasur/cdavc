"""Offline benchmark runner for the CD-AVC verification cage.

The module deliberately has a small surface area.  ``BenchmarkTask`` describes
one reproducible coding task, ``BenchmarkRunner`` records one JSON object per
task/arm, and ``render_report`` turns those records into a reviewable report.
The runner never sends a request to a remote endpoint: OpenAI-compatible
providers are accepted only when their endpoint resolves to the local machine.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import inspect
import json
import os
import platform
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import urlparse

from .invariants import has_raise_statement, required_exception
from .payloads import parse_payload
from .providers import (
    MockProvider,
    OpenAICompatibleProvider,
    ProviderCompletion,
    ProviderUnavailableError,
    SamplingParams,
)
from .redact import redact_paths
from .accounting import Budget, BudgetExceeded, UsageLedger, complete_recorded, digest as fingerprint_digest
from .edits import apply_candidate
from .properties import PropertyCase
from .verification import ArtifactStore, VerificationContract, WorkspaceSnapshot, candidate_payload, run_command, verify_workspace
from .context import ContextSession, is_context_request


ARMS = ("baseline_single", "baseline_retry", "cdavc", "cdavc_sampled", "cdavc_sampled_repair")
"""The stable order and names used in benchmark records."""

CAGE_ARMS = ("cdavc", "cdavc_sampled", "cdavc_sampled_repair")
"""Arms whose candidate must pass every verification gate before it is accepted."""

DEFAULT_COMMAND = ("python", "-m", "unittest", "discover", "-s", "tests")
BENCHMARK_VERSION = "5"
EVALUATION_PROTOCOL = "public-selection-heldout-once-v1"
DEFAULT_SAMPLES = 4
"""Independent draws a sampled arm may spend on one task."""

MAX_CANDIDATE_CHARS = 4000
"""Per-file cap when a repair prompt quotes the candidate it is repairing."""

HIDDEN_GATE_LABEL = "hidden test"
"""Gate label whose diagnostics must never reach a repair prompt."""

STDLIB_CONSTRAINT = (
    "The evaluation environment has no third-party packages: use the Python standard library only."
)
"""Environment fact every arm is told, so the arms differ only in verification."""

JSON_REASK_SUFFIX = (
    "\nYour previous reply could not be parsed as the required JSON object. "
    'Return only one valid JSON object of the form {"files": {"<path>": "<complete file contents>"}} '
    "with no prose, no markdown fence and no unescaped control characters.\n"
)

JSON_FAILURE_MARKERS = ("JSON", "files object", "file paths and contents")

BOUNDARY_PROBE = """\
import importlib.util
import json
import os
import sys

spec = json.loads(sys.argv[1])
for path in spec["files"]:
    directory = os.path.dirname(path)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    loader = importlib.util.spec_from_file_location("cdavc_boundary_probe", path)
    module = importlib.util.module_from_spec(loader)
    try:
        loader.loader.exec_module(module)
    except Exception as exc:
        # An unimportable module is the targeted test's problem, not this gate's.
        print(f"could not load {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    for symbol in spec["symbols"]:
        function = getattr(module, symbol, None)
        if not callable(function):
            continue
        for arguments in ((), ("",), ([],), (0,)):
            try:
                function(*arguments)
            except (IndexError, ZeroDivisionError) as exc:
                print(f"{symbol}{arguments!r} raised {type(exc).__name__}: {exc}", file=sys.stderr)
                raise SystemExit(1)
            except Exception:
                # Wrong-arity or wrong-type calls are not this gate's business.
                continue
"""
"""Opt-in gate that fuzzes each symbol with empty and zero inputs."""


class BenchmarkError(RuntimeError):
    """Raised for invalid benchmark configuration or unavailable execution."""


class _GateFailure(RuntimeError):
    """Internal failure whose message is safe to place in a model prompt."""


@dataclass(frozen=True)
class BenchmarkTask:
    """A single task evaluated by each benchmark arm.

    Commands are argv tuples and are never passed through a shell.  The
    defaults mirror the existing :class:`cdavc.supervisor.Supervisor` gates.
    ``locked_test_hashes`` is optional; when omitted, hashes are captured from
    the repository before the first arm and written into every record.
    """

    task_id: str
    title: str = ""
    description: str = ""
    source: str = "unspecified"
    implementation_files: tuple[str, ...] = ()
    test_files: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    test_command: tuple[str, ...] = DEFAULT_COMMAND
    hidden_test_command: tuple[str, ...] | None = None
    regression_command: tuple[str, ...] | None = DEFAULT_COMMAND
    negative_test_command: tuple[str, ...] | None = None
    boundary_probe: bool = False
    max_retries: int = 2
    locked_test_hashes: Mapping[str, str] | None = None
    properties: tuple[PropertyCase, ...] = ()
    check_repeats: int = 1
    context_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id:
            raise BenchmarkError("task_id must be a non-empty string")
        if not isinstance(self.title, str):
            raise BenchmarkError("task title must be a string")
        if not isinstance(self.description, str):
            raise BenchmarkError("task description must be a string")
        if not isinstance(self.source, str) or not self.source:
            raise BenchmarkError("task source must be a non-empty string")
        object.__setattr__(self, "implementation_files", _paths(self.implementation_files, "implementation_files"))
        object.__setattr__(self, "test_files", _paths(self.test_files, "test_files"))
        if not self.implementation_files:
            raise BenchmarkError("at least one implementation file is required")
        if not self.test_files:
            raise BenchmarkError("at least one test file is required")
        object.__setattr__(self, "symbols", _strings(self.symbols, "symbols"))
        object.__setattr__(self, "invariants", _strings(self.invariants, "invariants"))
        object.__setattr__(self, "context_files", _paths(self.context_files, "context_files"))
        object.__setattr__(self, "test_command", _command(self.test_command, "test_command"))
        object.__setattr__(self, "hidden_test_command", _optional_command(self.hidden_test_command, "hidden_test_command"))
        object.__setattr__(self, "regression_command", _optional_command(self.regression_command, "regression_command"))
        object.__setattr__(self, "negative_test_command", _optional_command(self.negative_test_command, "negative_test_command"))
        if not isinstance(self.boundary_probe, bool):
            raise BenchmarkError("boundary_probe must be a boolean")
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise BenchmarkError("max_retries must be a non-negative integer")
        if self.locked_test_hashes is not None:
            if not isinstance(self.locked_test_hashes, Mapping):
                raise BenchmarkError("locked_test_hashes must be a mapping")
            hashes = dict(self.locked_test_hashes)
            if not all(isinstance(path, str) and isinstance(value, str) for path, value in hashes.items()):
                raise BenchmarkError("locked_test_hashes must map paths to strings")
            _paths(tuple(hashes), "locked_test_hashes")
            object.__setattr__(self, "locked_test_hashes", hashes)
        contract = VerificationContract.from_task(self)
        object.__setattr__(self, "properties", contract.properties)

    @property
    def id(self) -> str:
        """Compatibility alias for the task graph's ``Task.id`` field."""

        return self.task_id

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BenchmarkTask":
        """Build a task from a JSON object or an existing task graph object."""

        if not isinstance(payload, Mapping):
            raise BenchmarkError("benchmark task must be an object")
        task_id = payload.get("task_id", payload.get("id"))
        if task_id is None:
            raise BenchmarkError("benchmark task requires task_id")
        return cls(
            task_id=task_id,
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            source=payload.get("source", "unspecified"),
            implementation_files=payload.get("implementation_files", ()),
            test_files=payload.get("test_files", ()),
            symbols=payload.get("symbols", ()),
            invariants=payload.get("invariants", ()),
            test_command=payload.get("test_command", DEFAULT_COMMAND),
            hidden_test_command=payload.get("hidden_test_command"),
            regression_command=payload.get("regression_command", DEFAULT_COMMAND),
            negative_test_command=payload.get("negative_test_command"),
            boundary_probe=payload.get("boundary_probe", False),
            max_retries=payload.get("max_retries", 2),
            locked_test_hashes=payload.get("locked_test_hashes"),
            properties=payload.get("properties", ()),
            check_repeats=payload.get("check_repeats", 1),
            context_files=payload.get("context_files", ()),
        )

    @classmethod
    def from_task(cls, task: Any) -> "BenchmarkTask":
        """Convert an existing ``cdavc.graph.Task`` without importing it."""

        if isinstance(task, cls):
            return task
        if isinstance(task, Mapping):
            return cls.from_dict(task)
        values = {
            "task_id": getattr(task, "task_id", getattr(task, "id", None)),
            "title": getattr(task, "title", ""),
            "description": getattr(task, "description", ""),
            "source": getattr(task, "source", "unspecified"),
            "implementation_files": getattr(task, "implementation_files", ()),
            "test_files": getattr(task, "test_files", ()),
            "symbols": getattr(task, "symbols", ()),
            "invariants": getattr(task, "invariants", ()),
            "test_command": getattr(task, "test_command", DEFAULT_COMMAND),
            "hidden_test_command": getattr(task, "hidden_test_command", None),
            "regression_command": getattr(task, "regression_command", DEFAULT_COMMAND),
            "negative_test_command": getattr(task, "negative_test_command", None),
            "boundary_probe": getattr(task, "boundary_probe", False),
            "max_retries": getattr(task, "max_retries", 2),
            "locked_test_hashes": getattr(task, "locked_test_hashes", None),
            "properties": getattr(task, "properties", ()),
            "check_repeats": getattr(task, "check_repeats", 1),
            "context_files": getattr(task, "context_files", ()),
        }
        return cls(**values)


@dataclass(frozen=True)
class _Attempt:
    passed: bool
    prompt_tokens: int | None
    completion_tokens: int | None
    failure: str = ""
    draw: int = 1
    seed: int | None = None
    json_reasks: int = 0


class BenchmarkRunner:
    """Run the benchmark arms and append resumable JSONL records."""

    def __init__(
        self,
        root: Path | str,
        provider: Any = None,
        *,
        provider_factory: Callable[[str, BenchmarkTask], Any] | None = None,
        tasks: Iterable[BenchmarkTask | Mapping[str, Any] | Any] = (),
        records_path: Path | str | None = None,
        report_path: Path | str | None = None,
        seed: int = 0,
        model: str | None = None,
        quantisation: str | None = None,
        version: str | None = None,
        hardware: str | None = None,
        timeout_seconds: float = 30.0,
        retry_cap: int = 3,
        samples: int = DEFAULT_SAMPLES,
        budget: Budget | None = None,
        context_budget_chars: int = 12000,
        max_context_requests: int = 2,
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise BenchmarkError(f"benchmark root does not exist: {self.root}")
        if provider is not None and provider_factory is not None:
            raise BenchmarkError("provide provider or provider_factory, not both")
        self.provider = provider_factory if provider_factory is not None else provider
        if self.provider is None:
            raise BenchmarkError("a provider or provider_factory is required")
        self.tasks = _load_tasks(tasks)
        if not self.tasks:
            raise BenchmarkError("at least one benchmark task is required")
        task_ids = [task.task_id for task in self.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise BenchmarkError("benchmark task ids must be unique")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise BenchmarkError("seed must be a non-negative integer")
        if timeout_seconds <= 0:
            raise BenchmarkError("timeout_seconds must be greater than zero")
        if isinstance(retry_cap, bool) or not isinstance(retry_cap, int) or retry_cap < 0:
            raise BenchmarkError("retry_cap must be a non-negative integer")
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
            raise BenchmarkError("samples must be a positive integer")
        self.seed = seed
        self.model = model
        self.quantisation = quantisation
        self.version = version
        self.hardware = hardware
        self.timeout_seconds = timeout_seconds
        self.retry_cap = retry_cap
        self.samples = samples
        self.budget = budget or Budget()
        if isinstance(context_budget_chars, bool) or not isinstance(context_budget_chars, int) or context_budget_chars < 512:
            raise BenchmarkError("context_budget_chars must be at least 512")
        if isinstance(max_context_requests, bool) or not isinstance(max_context_requests, int) or max_context_requests < 0:
            raise BenchmarkError("max_context_requests must be nonnegative")
        self.context_budget_chars, self.max_context_requests = context_budget_chars, max_context_requests
        if records_path is None:
            output_path = self.root / "results" / "benchmark.jsonl"
        else:
            output_path = Path(records_path)
            if not output_path.is_absolute():
                output_path = self.root / output_path
        self.records_path = output_path.resolve()
        report = Path(report_path) if report_path is not None else self.records_path.parent / "REPORT.md"
        self.report_path = (report if report.is_absolute() else self.root / report).resolve()
        if self.report_path == self.records_path:
            raise BenchmarkError("report and records paths must be different")
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        excluded = tuple(path.relative_to(self.root).as_posix() for path in (self.records_path, self.report_path)
                         if path.is_relative_to(self.root))
        self.snapshot = WorkspaceSnapshot.capture(self.root, exclude_paths=excluded)
        self.artifacts = ArtifactStore(self.root / ".cdavc" / "artifacts")
        self._last_evidence: dict[str, Any] | None = None
        self._records = _read_records(self.records_path)
        self._keys = {(record.get("task_id"), record.get("arm")) for record in self._records}
        self.experiment_config = self._experiment_config()
        self.experiment_fingerprint = fingerprint_digest(self.experiment_config)
        self._validate_resume_metadata()

    def _experiment_config(self) -> dict[str, Any]:
        paths: set[str] = set()
        for task in self.tasks:
            paths.update(task.implementation_files)
            paths.update(task.test_files)
            paths.update(task.locked_test_hashes or {})
            for command in (task.test_command, task.hidden_test_command, task.regression_command, task.negative_test_command):
                for word in command or ():
                    path = self.root / word
                    if not Path(word).is_absolute() and path.is_file() and path.resolve().is_relative_to(self.root):
                        paths.add(word)
        return {
            "protocol": EVALUATION_PROTOCOL, "runner_version": BENCHMARK_VERSION,
            "snapshot_digest": self.snapshot.digest,
            "tasks": [asdict(task) for task in self.tasks],
            "source_hashes": {path: _sha256(self.root / path) if (self.root / path).is_file() else None
                              for path in sorted(paths)},
            "engine_hashes": {path.name: _sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))},
            "python": list(sys.version_info[:3]), "seed": self.seed, "model": self.model,
            "quantisation": self.quantisation, "version": self.version, "hardware": self.hardware,
            "timeout_seconds": self.timeout_seconds, "retry_cap": self.retry_cap, "samples": self.samples,
            "budget": self.budget.to_dict(),
            "context_budget_chars": self.context_budget_chars, "max_context_requests": self.max_context_requests,
            "provider": {name: getattr(self.provider, name, None) for name in ("model", "timeout")},
            "sampling": self._sampling_config(),
            "endpoint_digest": fingerprint_digest(getattr(self.provider, "endpoint", None)),
        }

    def _sampling_config(self) -> dict[str, Any] | None:
        """Sampling controls belong in the fingerprint: they change candidate quality."""
        sampling = getattr(self.provider, "sampling", None)
        return sampling.to_dict() if sampling is not None else None

    def _validate_resume_metadata(self) -> None:
        """Prevent a resumed JSONL from silently mixing experiment configs."""

        expected = {
            "seed": self.seed,
            "model": self.model,
            "quantisation": self.quantisation,
            "version": self.version,
            "hardware": self.hardware,
        }
        for record in self._records:
            for field_name, configured in expected.items():
                if configured is not None and record.get(field_name) not in {None, configured}:
                    raise BenchmarkError(
                        f"resume metadata mismatch for {field_name}: "
                        f"record has {record.get(field_name)!r}, requested {configured!r}"
                    )
            if record.get("experiment_fingerprint") != self.experiment_fingerprint:
                raise BenchmarkError("resume fingerprint mismatch: use a new records file for incompatible or legacy runs")
        if len(self._keys) != len(self._records):
            raise BenchmarkError("duplicate task/arm records cannot resume")

    def run(self) -> list[dict[str, Any]]:
        """Run missing task/arm pairs and return all records, oldest first."""

        for task in self.tasks:
            hashes = self._lock_test_hashes(task)
            missing = [arm for arm in ARMS if (task.task_id, arm) not in self._keys]
            existing_hashes = {
                tuple(sorted(record.get("locked_test_hashes", {}).items()))
                for record in self._records
                if record.get("task_id") == task.task_id and isinstance(record.get("locked_test_hashes"), Mapping)
            }
            if existing_hashes and any(dict(items) != hashes for items in existing_hashes):
                raise BenchmarkError(f"locked test hashes changed for resumed task: {task.task_id}")
            if not missing:
                continue
            for arm in missing:
                key = (task.task_id, arm)
                if key in self._keys:
                    continue
                record = self._run_arm(task, arm, hashes)
                self._append_record(record)
        return list(self._records)

    def _run_arm(self, task: BenchmarkTask, arm: str, hashes: Mapping[str, str]) -> dict[str, Any]:
        if arm not in ARMS:
            raise BenchmarkError(f"unknown benchmark arm: {arm}")
        started = time.perf_counter()
        meter = _MemoryMeter()
        attempts: list[_Attempt] = []
        failure = ""
        previous_candidate = ""
        gates: list[str] = []
        accepted = False
        heldout_pass: bool | None = None
        evaluation_failure = ""
        reported_model: str | None = None
        ledger = UsageLedger(self.budget)
        outcome = ""
        selected: dict[str, Any] | None = None
        evidence_log: list[dict[str, Any]] = []
        verification_evidence: dict[str, Any] | None = None
        provider = self._provider_for(arm, task)
        self._ensure_local_provider(provider)
        cage_arm = arm in CAGE_ARMS
        # ``cdavc_sampled`` draws independent candidates; ``cdavc_sampled_repair``
        # spends the same draw budget but carries the previous public-gate failure
        # into the next draw, which separates the budget from the feedback effect.
        sampled = arm == "cdavc_sampled"
        if arm == "baseline_single":
            draw_budget = 1
        elif arm in ("cdavc_sampled", "cdavc_sampled_repair"):
            draw_budget = self.samples
        else:
            draw_budget = min(task.max_retries, self.retry_cap) + 1
        execution_mode = "fresh-snapshot-copy"
        try:
            for draw in range(1, draw_budget + 1):
                try:
                    ledger.check(before_call=True)
                except BudgetExceeded as exc:
                    outcome, failure = exc.outcome, str(exc)
                    break
                with self._execution_directory(arm) as workspace:
                    original = {path: _read_optional(workspace / path) for path in task.implementation_files}
                    # Test hashes include private evaluator inputs. Only implementation
                    # source and explicitly published context enter generation prompts.
                    paths = tuple(dict.fromkeys((*task.implementation_files, *task.context_files)))
                    paths = tuple(path for path in paths if (workspace / path).is_file())
                    session = ContextSession(workspace, paths, query=" ".join((task.title, task.description, *task.symbols)),
                                             max_chars=self.context_budget_chars)
                    context = session.initial()
                    # ``cdavc_sampled`` draws each candidate independently: no repair
                    # feedback is carried over, so repeated draws are real samples.
                    prompt = self._prompt(
                        task,
                        arm,
                        "" if sampled else failure,
                        draw=draw,
                        candidate="" if sampled else previous_candidate,
                        context=context,
                    )
                    usage: list[ProviderCompletion] = []
                    seed = self._draw_seed(task.task_id, draw)
                    self._last_evidence = None
                    call_start = len(ledger.entries)
                    try:
                        completion = self._generate(provider, prompt, task, arm, draw, workspace, usage, ledger, session, context)
                        if completion.model:
                            reported_model = completion.model
                        if cage_arm:
                            gates = self._run_cage_gates(task, workspace, hashes)
                        else:
                            self._run_baseline_test(task, workspace)
                        ledger.check()
                        selected = candidate_payload(workspace, VerificationContract.from_task(task))
                        verification_evidence = self._last_evidence
                        if verification_evidence:
                            evidence_log.append(verification_evidence)
                        reasks = sum(call["purpose"] == "json_reask" for call in ledger.entries[call_start:])
                        attempts.append(_attempt_record(True, usage, draw, seed, json_reasks=reasks))
                        failure = ""
                        break
                    except Exception as exc:  # bounded candidate failures become data, not runner crashes
                        failure = _safe_failure(exc)
                        # Capture what the model wrote before the workspace is restored:
                        # the next draw repairs that candidate instead of re-deriving it.
                        previous_candidate = self._candidate_context(task, workspace, original)
                        reasks = sum(call["purpose"] == "json_reask" for call in ledger.entries[call_start:])
                        attempts.append(_attempt_record(False, usage, draw, seed, failure, json_reasks=reasks))
                        if self._last_evidence:
                            evidence_log.append(self._last_evidence)
                            verification_evidence = self._last_evidence
                            if self._last_evidence["outcome"] in {"environment_failure", "inconclusive"}:
                                outcome = self._last_evidence["outcome"]
                                break
                        if isinstance(exc, BudgetExceeded):
                            outcome = exc.outcome
                            break
                        if isinstance(exc, ProviderUnavailableError):
                            outcome = "environment_failure"
                            break
            accepted = selected is not None
            # Held-out scoring executes once, in a new copy of the original
            # snapshot with the selected immutable artifact. Never re-enter draws.
            if accepted:
                with self._execution_directory(arm) as workspace:
                    try:
                        ledger.check()
                        apply_candidate(workspace, task.implementation_files, selected)
                        self._run_final_evaluation(task, workspace)
                        heldout_pass = True
                        ledger.check()
                    except BudgetExceeded as exc:
                        outcome = exc.outcome
                        evaluation_failure = str(exc)
                    except Exception as exc:
                        heldout_pass = False
                        evaluation_failure = _safe_failure(exc)
        except BenchmarkError:
            raise
        except Exception as exc:
            failure = _safe_failure(exc)
            attempts.append(_Attempt(False, None, None, failure))

        elapsed = time.perf_counter() - started
        passed = accepted and heldout_pass is True and outcome not in {"budget_exhausted", "inconclusive", "environment_failure"}
        accounting = ledger.summary()
        token_in, token_out = accounting["token_in"], accounting["token_out"]
        hidden_rejections = int(accepted and _is_hidden_failure(_failure_category(evaluation_failure)))
        accepted_on = next((index for index, item in enumerate(attempts, 1) if item.passed), None)
        record = {
            "task_id": task.task_id,
            "arm": arm,
            "task_source": task.source,
            "evaluation_protocol": EVALUATION_PROTOCOL,
            "experiment_fingerprint": self.experiment_fingerprint,
            "experiment_config": self.experiment_config,
            "budget": self.budget.to_dict(),
            "outcome": outcome or ("accepted_under_declared_checks" if accepted else "rejected_with_counterexample"),
            "accepted": accepted,
            "heldout_pass": heldout_pass,
            "selection_failure": failure,
            "evaluation_failure": evaluation_failure,
            "pass": passed,
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "attempts": len(attempts),
            "wall_time_seconds": float(elapsed),
            "wall_time": float(elapsed),
            "token_in": token_in,
            "token_out": token_out,
            "tokens_in": token_in,
            "tokens_out": token_out,
            "token_usage_source": accounting["token_usage_source"],
            "usage_complete": accounting["usage_complete"],
            "provider_calls": accounting["calls"],
            "unmetered_calls": accounting["unmetered_calls"],
            "known_token_in": accounting["known_token_in"],
            "known_token_out": accounting["known_token_out"],
            "call_log": ledger.entries,
            "verification_evidence": verification_evidence,
            "attempt_evidence": evidence_log,
            "artifact_digest": self.artifacts.put(selected) if selected is not None else None,
            "peak_memory_bytes": meter.finish(),
            "peak_memory_source": meter.source,
            "peak_memory_scope": "benchmark harness process",
            "model": self._metadata_value("model", provider, reported_model),
            "sampling": self._sampling_config(),
            "quantisation": self._metadata_value("quantisation", provider),
            "quantization": self._metadata_value("quantisation", provider),
            "version": self._metadata_value("version", provider),
            "runner_version": BENCHMARK_VERSION,
            "hardware": self.hardware or platform.platform(),
            "seed": self.seed,
            "samples_budget": draw_budget,
            "samples_drawn": len(attempts),
            "samples_to_accept": accepted_on,
            "json_reasks": sum(item.json_reasks for item in attempts),
            "verifier_gap": bool(cage_arm and hidden_rejections),
            "verifier_gap_attempts": hidden_rejections if cage_arm else 0,
            "attempt_log": [
                {
                    "attempt": index,
                    "draw": item.draw,
                    "seed": item.seed,
                    "status": "ACCEPTED" if item.passed else "REJECTED",
                    **({"failure": item.failure} if item.failure else {}),
                    **({"json_reasks": item.json_reasks} if item.json_reasks else {}),
                }
                for index, item in enumerate(attempts, 1)
            ],
            "failure": "" if passed else evaluation_failure or failure,
            "execution_mode": execution_mode,
            "cage_gates_run": cage_arm,
            "gate_results": gates,
            "locked_test_hashes": dict(hashes),
            "ast_contract": {"files": list(task.implementation_files), "symbols": list(task.symbols)},
            "cage_rejected_bad_patch_arm_a_would_have_shipped": (
                cage_arm and not passed and self._baseline_single_passed(task.task_id)
            ),
        }
        record["cage_rejected_bad_patch"] = record["cage_rejected_bad_patch_arm_a_would_have_shipped"]
        return record

    def _baseline_single_passed(self, task_id: str) -> bool:
        for record in reversed(self._records):
            if record.get("task_id") == task_id and record.get("arm") == "baseline_single":
                return _record_passed(record)
        return False

    def _provider_for(self, arm: str, task: BenchmarkTask) -> Any:
        if isinstance(self.provider, Mapping):
            try:
                return self.provider[arm]
            except KeyError as exc:
                raise BenchmarkError(f"provider mapping has no arm: {arm}") from exc
        if hasattr(self.provider, "complete") or hasattr(self.provider, "complete_with_metadata"):
            return self.provider
        if not callable(self.provider):
            raise BenchmarkError("provider must implement complete() or be a provider factory")
        try:
            parameters = inspect.signature(self.provider).parameters.values()
        except (TypeError, ValueError):
            parameters = ()
        positional = [
            parameter
            for parameter in parameters
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        accepts_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters)
        if accepts_varargs or len(positional) >= 2:
            return self.provider(arm, task)
        return self.provider(arm)

    def _draw_seed(self, task_id: str, draw: int) -> int:
        """Derive an independent sampling seed for one draw of one task.

        Passing the run seed unchanged on every attempt restarted the same
        sampler stream, so retries were near-duplicates.  Drawing 1 is derived
        identically for every arm, which keeps the arms paired.
        """

        material = f"{self.seed}:{task_id}:{draw}".encode("utf-8")
        digest = hashlib.blake2s(material, digest_size=8).digest()
        return int.from_bytes(digest, "big") % (2**31 - 1)

    def _complete(self, provider: Any, prompt: str, task: BenchmarkTask, arm: str, draw: int,
                  ledger: UsageLedger, *, purpose: str = "generation") -> ProviderCompletion:
        del arm
        seed = self._draw_seed(task.task_id, draw)
        messages = [{"role": "user", "content": prompt}]
        return complete_recorded(provider, messages, ledger, purpose=purpose, seed=seed)

    def _generate(
        self,
        provider: Any,
        prompt: str,
        task: BenchmarkTask,
        arm: str,
        draw: int,
        workspace: Path,
        usage: list[ProviderCompletion],
        ledger: UsageLedger,
        session: ContextSession,
        context: str,
    ) -> ProviderCompletion:
        """Draw one candidate, asking once more if the reply is not JSON.

        A formatting slip is not a failed attempt: re-asking costs tokens but
        does not consume the arm's draw budget, and the extra call is counted
        in ``json_reasks``.
        """

        purpose, next_prompt, requested, reasked = "generation", prompt, 0, False
        while True:
            completion = self._complete(provider, next_prompt, task, arm, draw, ledger, purpose=purpose)
            usage.append(completion)
            try:
                try:
                    payload = parse_payload(completion.text)
                except ValueError:
                    payload = None
                if is_context_request(payload):
                    if requested >= self.max_context_requests:
                        raise BudgetExceeded("context request budget exhausted")
                    retrieved = session.respond(payload)
                    next_prompt, purpose = prompt.replace(context, retrieved, 1), "context_retrieval"
                    requested += 1
                    continue
                self._apply_response(task, completion.text, workspace)
                return completion
            except _GateFailure as exc:
                if reasked or not _is_json_failure(exc):
                    raise
                next_prompt += JSON_REASK_SUFFIX
                purpose, reasked = "json_reask", True

    def _prompt(
        self,
        task: BenchmarkTask,
        arm: str,
        previous_failure: str,
        *,
        draw: int = 1,
        candidate: str = "",
        context: str = "",
    ) -> str:
        specification = f"\nTask specification: {task.description}\n" if task.description else ""
        previous = ""
        if candidate:
            previous = (
                "\nPrevious candidate, which failed the gates below; repair it instead of starting over:\n"
                f"{candidate}\n"
            )
        repair = ""
        if previous_failure:
            if arm == "baseline_retry":
                repair = f"\nPrevious failing output; repair the candidate using only this output:\n{previous_failure}\n"
            elif arm in CAGE_ARMS:
                repair = self._cage_repair(task, previous_failure)
        examples = ", ".join(f'"{path}": "complete file contents"' for path in task.implementation_files)
        if not examples:
            examples = '"src/example.py": "complete file contents"'
        return (
            f"Implement task {task.task_id}: {task.title}.\n"
            f"Deterministic seed: {self._draw_seed(task.task_id, draw)}.\n"
            + specification
            + f"Allowed implementation files: {', '.join(task.implementation_files)}\n"
            f"Required symbols: {', '.join(task.symbols) or '(none)'}\n"
            f"Public invariants: {', '.join(task.invariants) or '(see tests)'}\n"
            f"{STDLIB_CONSTRAINT}\n"
            f'Return only JSON in the form {{"files": {{{examples}}}}}. '
            "Use repository-relative paths, modify only allowed implementation files, and never modify tests.\n"
            + context
            + previous
            + repair
        )

    def _candidate_context(
        self,
        task: BenchmarkTask,
        workspace: Path,
        original: Mapping[str, str | None],
    ) -> str:
        """Quote the files a rejected draw changed, so the next draw can repair them."""

        sections: list[str] = []
        for relative in task.implementation_files:
            try:
                content = (workspace / relative).read_bytes().decode("utf-8")
            except OSError:
                continue
            if content == original.get(relative):
                continue
            if len(content) > MAX_CANDIDATE_CHARS:
                content = content[:MAX_CANDIDATE_CHARS] + (
                    f"\n... truncated after {MAX_CANDIDATE_CHARS} characters ...\n"
                )
            sections.append(f"--- {relative} ---\n{content}")
        return "\n".join(sections)

    def _cage_repair(self, task: BenchmarkTask, failure: str) -> str:
        """Build cage repair context that never carries hidden assertions.

        Targeted, negative and regression tests are public repository assets,
        so their sanitised traceback is forwarded like a human engineer would
        see it.  A hidden-gate rejection stays categorical and is answered with
        the task's declared invariants instead of the failing assertion.
        """

        category = _failure_category(failure)
        context = f"\nPrevious deterministic failure category: {category}\n"
        if _is_hidden_failure(category):
            return context + _invariant_guidance(task)
        detail = failure.split(":", 1)[1].strip() if ":" in failure else ""
        if detail:
            return context + f"Public gate output:\n{detail}\n"
        return context

    def _apply_response(self, task: BenchmarkTask, response: str, workspace: Path) -> None:
        try:
            payload = parse_payload(response)
        except ValueError:
            raise _GateFailure("provider response is not a JSON files object")
        if not isinstance(payload, dict) or not ({"files", "edits"} & payload.keys()):
            raise _GateFailure("provider response is not a JSON files object")
        files = payload.get("files", {})
        if not isinstance(files, dict):
            raise _GateFailure("provider files object is empty")
        allowed = set(task.implementation_files)
        normalized_files: dict[str, Any] = {}
        basename_map = {Path(p).name: p for p in task.implementation_files}
        for path_key, content in files.items():
            if path_key in allowed:
                normalized_files[path_key] = content
            elif path_key in basename_map and len(task.implementation_files) == 1:
                normalized_files[basename_map[path_key]] = content
            else:
                normalized_files[path_key] = content
        if not set(normalized_files).issubset(allowed):
            raise _GateFailure("provider changed a file outside the implementation contract")
        try:
            apply_candidate(workspace, task.implementation_files, {**payload, "files": normalized_files})
        except ValueError as exc:
            raise _GateFailure(str(exc)) from exc

    def _run_baseline_test(self, task: BenchmarkTask, workspace: Path) -> None:
        contract = replace(VerificationContract.from_task(task), symbols=(), invariants=(), properties=(),
                           regression_command=None, negative_test_command=None, boundary_probe=False)
        self._verify_public(workspace, contract)

    def _run_final_evaluation(self, task: BenchmarkTask, workspace: Path) -> None:
        """Use one common final evaluator, never as a generation feedback oracle."""
        contract = replace(VerificationContract.from_task(task), symbols=(), invariants=(), properties=(),
                           negative_test_command=None, boundary_probe=False)
        # Preserve selection evidence; scoring evidence must not replace it.
        selection = self._last_evidence
        try:
            self._verify_public(workspace, contract)
        finally:
            self._last_evidence = selection
        if task.hidden_test_command:
            locked = {name: values["sha256"] for name, values in WorkspaceSnapshot.capture(workspace).manifest()["files"].items()}
            try:
                self._run_command(task.hidden_test_command, workspace, HIDDEN_GATE_LABEL)
            finally:
                _assert_test_hashes(workspace, locked)

    def _run_cage_gates(self, task: BenchmarkTask, workspace: Path, hashes: Mapping[str, str]) -> list[str]:
        _assert_test_hashes(workspace, hashes)
        return self._verify_public(workspace, VerificationContract.from_task(task))

    def _verify_public(self, workspace: Path, contract: VerificationContract) -> list[str]:
        evidence = verify_workspace(workspace, contract, snapshot=self.snapshot, store=self.artifacts,
                                    seed=self.seed, timeout_seconds=self.timeout_seconds, command_runner=self._run_command)
        self._last_evidence = evidence
        if not evidence["accepted"]:
            failure = _GateFailure(evidence["failure"])
            failure.evidence = evidence
            raise failure
        return evidence["gates"]

    def _run_boundary_probe(self, task: BenchmarkTask, workspace: Path) -> None:
        """Fuzz every declared symbol with empty and zero inputs."""

        payload = json.dumps(
            {
                "files": [str((workspace / relative).resolve()) for relative in task.implementation_files],
                "symbols": list(task.symbols),
            }
        )
        self._run_command((sys.executable, "-c", BOUNDARY_PROBE, payload), workspace, "boundary probe", include_output=True)

    def _run_command(
        self,
        command: Sequence[str],
        workspace: Path,
        label: str,
        *,
        include_output: bool = False,
    ) -> dict[str, Any]:
        receipt = run_command(command, workspace, label, timeout_seconds=self.timeout_seconds,
                              seed=self.seed, include_output=include_output)
        if receipt["status"] != "passed":
            failure = _GateFailure(receipt["failure"])
            failure.receipt = receipt
            raise failure
        return receipt

    def _execution_directory(self, arm: str) -> contextlib.AbstractContextManager[Path]:
        return self.snapshot.materialize()

    def _lock_test_hashes(self, task: BenchmarkTask) -> dict[str, str]:
        actual: dict[str, str] = {}
        for relative in task.test_files:
            path = self.root / relative
            if not path.is_file():
                raise BenchmarkError(f"declared test file does not exist: {relative}")
            actual[relative] = _sha256(path)
        expected = dict(task.locked_test_hashes or {})
        for relative, expected_hash in expected.items():
            if relative not in actual:
                path = self.root / relative
                if not path.is_file():
                    raise BenchmarkError(f"locked test file does not exist: {relative}")
                actual[relative] = _sha256(path)
            if actual[relative] != expected_hash:
                raise BenchmarkError(f"locked test hash mismatch: {relative}")
        return actual

    def _append_record(self, record: dict[str, Any]) -> None:
        key = (record["task_id"], record["arm"])
        if key in self._keys:
            return
        with self.records_path.open("a", encoding="utf-8") as handle:
            if self.records_path.stat().st_size:
                with self.records_path.open("rb") as existing:
                    existing.seek(-1, os.SEEK_END)
                    if existing.read(1) != b"\n":
                        handle.write("\n")
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._records.append(record)
        self._keys.add(key)

    def _ensure_local_provider(self, provider: Any) -> None:
        if isinstance(provider, OpenAICompatibleProvider) or hasattr(provider, "endpoint"):
            endpoint = getattr(provider, "endpoint", "")
            parsed = urlparse(endpoint)
            if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise BenchmarkError("benchmark providers must use a local OpenAI-compatible endpoint")

    def _metadata_value(self, name: str, provider: Any, reported: str | None = None) -> str | None:
        configured = getattr(self, name)
        if configured is not None:
            return configured
        value = reported if reported is not None else getattr(provider, name, None)
        if value is None and name == "quantisation":
            value = getattr(provider, "quantization", None)
        if isinstance(value, str) and value:
            return value
        if name == "model" and isinstance(provider, MockProvider):
            return "mock"
        return None


class _MemoryMeter:
    """Sample this harness process's resident set during one arm.

    The local model server is intentionally a separate process. Its memory is
    therefore not silently attributed to a task; the record names this scope.
    ``ps`` gives a current RSS on macOS and Linux, while the resource fallback
    remains available on platforms without that command.
    """

    def __init__(self) -> None:
        self.source = "unavailable"
        self._peak: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            initial = self._sample_ps()
        except (OSError, subprocess.SubprocessError):
            initial = None
        if initial is not None:
            self._peak = initial
            self.source = "ps RSS sampled for this benchmark arm; bytes"
            self._thread = threading.Thread(target=self._sample_loop, name="cdavc-memory", daemon=True)
            self._thread.start()
        else:
            try:
                import resource

                self._resource = resource
                self._peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                self.source = "resource.getrusage(RUSAGE_SELF).ru_maxrss; bytes on macOS, KiB on Linux"
            except (ImportError, AttributeError, OSError):
                self._resource = None

    def finish(self) -> int | None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            return self._peak
        resource = getattr(self, "_resource", None)
        if resource is None:
            return None
        try:
            value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if sys.platform.startswith("linux"):
                value *= 1024
            return max(int(self._peak or 0), value)
        except (AttributeError, OSError, ValueError):
            return None

    def _sample_loop(self) -> None:
        while not self._stop.wait(0.05):
            try:
                sample = self._sample_ps()
            except (OSError, subprocess.SubprocessError):
                return
            if sample is not None:
                self._peak = max(self._peak or 0, sample)

    @staticmethod
    def _sample_ps() -> int | None:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            capture_output=True,
            text=True,
            check=False,
            timeout=1.0,
        )
        if result.returncode:
            return None
        value = result.stdout.strip()
        if not value.isdigit():
            return None
        return int(value) * 1024


class _CopiedWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path | None = None

    def __enter__(self) -> Path:
        self._temporary = tempfile.TemporaryDirectory(prefix="cdavc-baseline-")
        self.path = Path(self._temporary.name) / self.root.name
        shutil.copytree(self.root, self.path, symlinks=True, ignore=_copy_ignore(self.root))
        return self.path

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()


class _GitWorktree:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path | None = None
        self._added = False

    def __enter__(self) -> Path:
        self._temporary = tempfile.TemporaryDirectory(prefix="cdavc-worktree-")
        self.path = Path(self._temporary.name) / self.root.name
        try:
            _git(self.root, "worktree", "add", "--detach", "--quiet", str(self.path), "HEAD")
            self._added = True
            # A worktree is the execution boundary, while the benchmark input
            # may contain deliberate uncommitted fixture edits.  Overlay the
            # current project after creating the real worktree so those edits
            # are measured without ever changing the source checkout.
            shutil.copytree(self.root, self.path, symlinks=True, dirs_exist_ok=True, ignore=_copy_ignore(self.root))
        except Exception as exc:
            if self._added and self.path is not None:
                try:
                    _git(self.root, "worktree", "remove", "--force", str(self.path))
                except OSError:
                    pass
            self._cleanup_temp()
            raise BenchmarkError("cdavc arm requires a git repository with a checked-out HEAD") from exc
        return self.path

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        if self._added and self.path is not None:
            try:
                _git(self.root, "worktree", "remove", "--force", str(self.path))
            finally:
                self._cleanup_temp()
        else:
            self._cleanup_temp()

    def _cleanup_temp(self) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()


def run_benchmark(
    root: Path | str,
    provider: Any,
    tasks: Iterable[BenchmarkTask | Mapping[str, Any] | Any],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Small functional wrapper around :class:`BenchmarkRunner`."""

    return BenchmarkRunner(root, provider, tasks=tasks, **kwargs).run()


def read_records(path: Path | str) -> list[dict[str, Any]]:
    """Read valid JSONL records without changing the append-only file."""

    return _read_records(Path(path))


def paired_pass_rate_difference(
    records: Sequence[Mapping[str, Any]],
    arm: str = "cdavc",
    baseline_arm: str = "baseline_single",
) -> dict[str, float | int | None]:
    """Return a paired pass-rate delta and normal-approximation 95% CI."""

    by_key = {(record.get("task_id"), record.get("arm")): record for record in records}
    differences: list[float] = []
    for task_id in sorted({record.get("task_id") for record in records if record.get("task_id") is not None}):
        left = by_key.get((task_id, arm))
        right = by_key.get((task_id, baseline_arm))
        if left is None or right is None:
            continue
        differences.append(float(_record_passed(left)) - float(_record_passed(right)))
    if not differences:
        return {"n": 0, "difference": None, "delta": None, "ci95_low": None, "ci95_high": None, "ci95": None}
    difference = statistics.mean(differences)
    if len(differences) == 1:
        margin = 0.0
    else:
        margin = 1.96 * statistics.stdev(differences) / (len(differences) ** 0.5)
    return {
        "n": len(differences),
        "difference": difference,
        "delta": difference,
        "ci95_low": max(-1.0, difference - margin),
        "ci95_high": min(1.0, difference + margin),
        "ci95": (max(-1.0, difference - margin), min(1.0, difference + margin)),
    }


def wilson_interval(passed: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval for a pass rate; ``None`` when no records exist."""

    if total <= 0:
        return None
    proportion = passed / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = (z / denominator) * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5)
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def render_report(records: Sequence[Mapping[str, Any]] | Path | str) -> str:
    """Render benchmark records with arm summaries and paired comparisons."""

    rows = _read_records(Path(records)) if isinstance(records, (Path, str)) else list(records)
    summaries = {arm: _arm_summary(rows, arm) for arm in ARMS}
    cage_difference = paired_pass_rate_difference(rows, "cdavc", "baseline_single")
    sampled_difference = paired_pass_rate_difference(rows, "cdavc_sampled", "baseline_single")
    repair_difference = paired_pass_rate_difference(rows, "cdavc_sampled_repair", "baseline_single")
    lines = [
        "# CD-AVC benchmark report",
        "",
        "All values below are measured records from this run. An em dash means the local provider did not report a value; no value is estimated.",
        "Budget disclosure: differing draw limits and incomplete telemetry are not matched-token evidence. "
        "These summaries do not establish model superiority or token savings. Use the explicit-cap external comparison workflow for qualified frozen-artifact comparisons.",
        "",
        ("Fairness disclosure: public checks alone select candidates. Held-out scoring runs once after selection, "
         "never triggers another generation, and never feeds a repair prompt. Acceptance and held-out success are recorded separately. "
         "All arms use the same initial prompt and common final evaluator; retries and independent samples have different draw budgets."
         if rows and all(row.get("evaluation_protocol") == EVALUATION_PROTOCOL for row in rows)
         else "Fairness disclosure: historical or unrecorded evaluation protocols are present. Legacy runs may use hidden "
         "feedback or hidden-oracle selection and must not be treated as deployable public-selection comparisons."),
        "",
        "| Arm | Records | Passed | Pass rate | 95% CI (Wilson) | Mean attempts | Mean wall (s) | Mean token in | Mean token out |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        summary = summaries[arm]
        lines.append(
            f"| `{arm}` | {summary['records']} | {summary['passed']} | {_percent(summary['pass_rate'])} | "
            f"{_wilson_text(summary['passed'], summary['records'])} | "
            f"{_number(summary['mean_attempts'])} | {_number(summary['mean_wall_time'])} | "
            f"{_number(summary['mean_token_in'])} | {_number(summary['mean_token_out'])} |"
        )

    provenance: dict[str, int] = {}
    for record in rows:
        label = str(record.get("runner_version") or "unrecorded")
        provenance[label] = provenance.get(label, 0) + 1
    if len(provenance) > 1:
        lines.extend(
            [
                "",
                "## Record provenance",
                "",
                "Task/arm pairs measured under more than one runner version are present; each pair is scored entirely by the version that measured it.",
                "",
                "| Runner version | Records |",
                "|---|---:|",
            ]
        )
        for label in sorted(provenance):
            lines.append(f"| `{label}` | {provenance[label]} |")

    lines.extend(["", "## Paired pass-rate differences", "", "| Comparison | N | Difference | 95% CI |", "|---|---:|---:|---:|"])
    for arm, baseline in (
        ("baseline_retry", "baseline_single"),
        ("cdavc", "baseline_single"),
        ("cdavc_sampled", "baseline_single"),
        ("cdavc_sampled", "baseline_retry"),
        ("cdavc_sampled", "cdavc"),
        ("cdavc_sampled_repair", "baseline_single"),
        ("cdavc_sampled_repair", "baseline_retry"),
        ("cdavc_sampled_repair", "cdavc"),
        ("cdavc_sampled_repair", "cdavc_sampled"),
    ):
        difference = paired_pass_rate_difference(rows, arm, baseline)
        lines.append(
            f"| `{arm}` − `{baseline}` | {difference['n']} | {_number(difference['difference'])} | "
            f"{_ci_text(difference)} |"
        )

    lines.extend(
        [
            "",
            "## Measured result",
            "",
            _result_sentence("cdavc_sampled", sampled_difference),
            _result_sentence("cdavc_sampled_repair", repair_difference),
            _result_sentence("cdavc", cage_difference),
            _result_sentence(
                "cdavc_sampled", paired_pass_rate_difference(rows, "cdavc_sampled", "baseline_retry"), "baseline_retry"
            ),
            _result_sentence(
                "cdavc_sampled_repair",
                paired_pass_rate_difference(rows, "cdavc_sampled_repair", "cdavc_sampled"),
                "cdavc_sampled",
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Sampling budget",
            "",
            "| Arm | Draw budget | Mean draws used | Mean draws to accept | JSON re-asks |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for arm in ARMS:
        summary = summaries[arm]
        lines.append(
            f"| `{arm}` | {_number(summary['mean_budget'])} | {_number(summary['mean_drawn'])} | "
            f"{_number(summary['mean_to_accept'])} | {summary['json_reasks']} |"
        )

    lines.extend(
        [
            "",
            "## Measured overhead vs baseline_single",
            "",
            "| Arm | Paired N | Mean time overhead (s) | Mean time overhead (%) | Mean token overhead |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for arm in ("baseline_retry", "cdavc", "cdavc_sampled", "cdavc_sampled_repair"):
        overhead = _overhead(rows, arm, "baseline_single")
        lines.append(
            f"| `{arm}` | {overhead['n']} | {_number(overhead['time_seconds'])} | {_percent(overhead['time_ratio'])} | {_number(overhead['tokens'])} |"
        )

    lines.extend(["", "## Measured verifier gap", ""])
    gaps = [
        (arm, sum(1 for record in rows if record.get("arm") == arm and record.get("verifier_gap")))
        for arm in CAGE_ARMS
    ]
    if any(count for _, count in gaps):
        for arm, count in gaps:
            lines.append(
                f"- `{arm}`: {count} task(s) where at least one candidate passed the public targeted test "
                "and was rejected by the hidden gate."
            )
    else:
        lines.append("None measured: no cage candidate passed the public gates and then failed the hidden gate.")

    lines.extend(["", "## Measured failure categories", ""])
    categories = failure_categories(rows)
    if categories:
        lines.append("| Category | " + " | ".join(f"`{arm}`" for arm in ARMS) + " |")
        lines.append("|---|" + "---:|" * len(ARMS))
        for category in categories:
            cells = [str(categories[category].get(arm, 0)) for arm in ARMS]
            lines.append(f"| {category} | " + " | ".join(cells) + " |")
    else:
        lines.append("None measured: every recorded arm passed its task.")

    lines.extend(["", "## Measured cage-hurt cases", ""])
    hurt = cage_hurt_cases(rows)
    if hurt:
        lines.append("| Task | baseline_single | cdavc |")
        lines.append("|---|---:|---:|")
        for item in hurt:
            lines.append(f"| `{item['task_id']}` | PASS | FAIL |")
    else:
        lines.append("None measured.")
    lines.append("")
    return "\n".join(lines)


def _result_sentence(arm: str, difference: Mapping[str, Any], baseline: str = "baseline_single") -> str:
    if difference.get("difference") is None:
        return f"Measured result: no paired `{arm}`/`{baseline}` records were available."
    value = float(difference["difference"])
    low = float(difference["ci95_low"])
    if value > 0 and low > 0:
        conclusion = "a measured pass-rate gain"
    elif value > 0:
        conclusion = "a measured positive difference, but not a conclusive gain because the 95% CI includes zero"
    elif value < 0:
        conclusion = "a measured negative pass-rate difference"
    else:
        conclusion = "no measured pass-rate gain"
    return (
        f"Measured result: `{arm}` shows {conclusion} of {value:.3f} "
        f"({value * 100:.1f} percentage points vs `{baseline}`; 95% CI {_ci_text(difference)}). "
        "This statement uses only completed paired records; it is not a projection."
    )


def failure_categories(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """Count final failure categories per arm, ordered by total occurrences.

    The same gate can word its first line differently between code paths ("AST contract
    failed" for a parse error, "AST Contract Failed" for a missing raise), so categories
    are grouped case-insensitively and shown with the first spelling a record used.
    """

    counts: Counter[tuple[str, str]] = Counter()
    spellings: dict[str, str] = {}
    for record in records:
        if record.get("arm") not in ARMS or _record_passed(record):
            continue
        category = _failure_category(str(record.get("failure") or "")) or "unclassified"
        key = category.casefold()
        spellings.setdefault(key, category)
        counts[(key, str(record["arm"]))] += 1
    keys = sorted({key for key, _ in counts}, key=lambda item: (-sum(counts[(item, arm)] for arm in ARMS), item))
    return {
        spellings[key]: {arm: counts[(key, arm)] for arm in ARMS if counts[(key, arm)]}
        for key in keys
    }


def cage_hurt_cases(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """List tasks passing baseline_single but failing the CD-AVC cage."""

    by_key = {(record.get("task_id"), record.get("arm")): record for record in records}
    task_ids = sorted({record.get("task_id") for record in records if record.get("task_id") is not None})
    result = []
    for task_id in task_ids:
        baseline = by_key.get((task_id, "baseline_single"))
        cage = by_key.get((task_id, "cdavc"))
        if baseline and cage and _record_passed(baseline) and not _record_passed(cage):
            result.append({"task_id": task_id, "baseline_single": True, "cdavc": False})
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CD-AVC local benchmark arms")
    parser.add_argument("root", type=Path, help="trusted git project root")
    parser.add_argument("--tasks", type=Path, required=True, help="JSON file containing a task list or {tasks: [...]}")
    parser.add_argument("--records", type=Path, default=None, help="append-only JSONL output path")
    parser.add_argument("--report", type=Path, default=None, help="Markdown report path; defaults to results/REPORT.md")
    parser.add_argument("--endpoint", default="", help="local OpenAI-compatible chat-completions endpoint")
    parser.add_argument("--model", default=None)
    parser.add_argument("--quantisation", default=None)
    parser.add_argument("--version", default=None)
    parser.add_argument("--hardware", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retry-cap", type=int, default=3)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="draw budget for the cdavc_sampled and cdavc_sampled_repair arms")
    parser.add_argument("--max-calls", type=int, help="provider call cap per task/arm, including re-asks and retrieval")
    parser.add_argument("--max-tokens", type=int, help="reported input+output cap; unmetered calls make the run inconclusive")
    parser.add_argument("--max-wall-seconds", type=float, help="wall-clock cap per task/arm")
    parser.add_argument("--context-budget", dest="context_budget_chars", type=int, default=12000)
    parser.add_argument("--max-context-requests", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=None, help="sampling temperature sent to the model server")
    parser.add_argument("--top-p", type=float, default=None, help="nucleus sampling bound sent to the model server")
    parser.add_argument("--top-k", type=int, default=None, help="top-k bound; accepted by llama.cpp, LM Studio, vLLM and Ollama")
    parser.add_argument("--max-output-tokens", type=int, default=None, help="completion length cap; truncated replies are rejected, not parsed")
    parser.add_argument("--limit", type=int, default=None, help="limit the number of tasks to run")
    parser.add_argument("--mock", action="store_true", help="use deterministic scripted responses instead of an endpoint")
    parser.add_argument("--mock-response", action="append", default=[], type=Path, help="JSON response file; may be repeated")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        task_payload = json.loads(args.tasks.read_text())
        raw_tasks = task_payload.get("tasks") if isinstance(task_payload, Mapping) else task_payload
        tasks = _load_tasks(raw_tasks or [])
        if args.limit is not None and args.limit > 0:
            tasks = tasks[: args.limit]
        if args.mock or args.mock_response:
            if args.mock_response:
                responses = [path.read_text() for path in args.mock_response]
                provider: Any = lambda _arm, _task: MockProvider(responses)
            else:
                provider = lambda _arm, task: _snapshot_mock_provider(args.root, task)
        else:
            if not args.endpoint:
                raise BenchmarkError("--endpoint is required unless --mock is selected")
            sampling = SamplingParams(temperature=args.temperature, top_p=args.top_p,
                                      top_k=args.top_k, max_tokens=args.max_output_tokens)
            provider = OpenAICompatibleProvider(
                args.endpoint,
                model=args.model or "local-model",
                timeout=args.timeout,
                sampling=None if sampling == SamplingParams() else sampling,
            )
        runner = BenchmarkRunner(
            args.root,
            provider,
            tasks=tasks,
            records_path=args.records,
            report_path=args.report,
            seed=args.seed,
            model=args.model,
            quantisation=args.quantisation,
            version=args.version,
            hardware=args.hardware,
            timeout_seconds=args.timeout,
            retry_cap=args.retry_cap,
            samples=args.samples,
            budget=Budget(args.max_calls, args.max_tokens, args.max_wall_seconds),
            context_budget_chars=args.context_budget_chars,
            max_context_requests=args.max_context_requests,
        )
        records = runner.run()
        output = render_report(records)
        runner.report_path.write_text(output)
        print(output, end="")
        selected_ids = {task.task_id for task in tasks}
        return 0 if all(_record_passed(record) for record in records if record.get("task_id") in selected_ids) else 1
    except (OSError, ValueError, BenchmarkError, ProviderUnavailableError) as exc:
        print(f"cdavc benchmark: {exc}", file=sys.stderr)
        return 2


def _load_tasks(tasks: Iterable[BenchmarkTask | Mapping[str, Any] | Any] | Path | str) -> list[BenchmarkTask]:
    if isinstance(tasks, (Path, str)):
        payload = json.loads(Path(tasks).read_text())
        tasks = payload.get("tasks", []) if isinstance(payload, Mapping) else payload
    return [BenchmarkTask.from_task(task) for task in tasks]


def _snapshot_mock_provider(root: Path, task: BenchmarkTask) -> MockProvider:
    """Return a checked-in deterministic candidate for the offline CI path.

    Mock mode intentionally uses a separate answer fixture rather than
    copying the incomplete task implementation.  This keeps ``--mock`` useful
    as a bounded end-to-end smoke run while leaving the benchmark corpus
    untouched for a real local-model run.
    """

    files = {}
    for relative in task.implementation_files:
        candidates = (
            root / "benchmarks" / "mock_solutions" / task.task_id / Path(relative).name,
            root / "benchmarks" / "mock_solutions" / task.task_id / "solution.py",
            root / relative,
        )
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise BenchmarkError(f"mock snapshot file does not exist for {task.task_id}: {relative}")
        files[relative] = path.read_text()
    response = json.dumps({"files": files})
    return MockProvider([response] * (task.max_retries + 1))


def _paths(value: Iterable[str], label: str) -> tuple[str, ...]:
    result = _strings(value, label)
    for path in result:
        pure = Path(path)
        if pure.is_absolute() or ".." in pure.parts or path == ".":
            raise BenchmarkError(f"{label} contains unsafe path: {path!r}")
    return result


def _strings(value: Iterable[str], label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise BenchmarkError(f"{label} must be a sequence of non-empty strings")
    try:
        result = tuple(value)
    except TypeError as exc:
        raise BenchmarkError(f"{label} must be a sequence of non-empty strings") from exc
    if not all(isinstance(item, str) and item for item in result):
        raise BenchmarkError(f"{label} must be a sequence of non-empty strings")
    return result


def _command(value: Sequence[str] | str, label: str) -> tuple[str, ...]:
    if isinstance(value, str):
        value = tuple(shlex.split(value))
    result = _strings(value, label)
    if not result:
        raise BenchmarkError(f"{label} cannot be empty")
    return result


def _optional_command(value: Sequence[str] | str | None, label: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _command(value, label)


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                # A process killed during a write leaves the append-only file
                # recoverable; valid prior records remain usable.
                continue
            if isinstance(value, dict) and isinstance(value.get("task_id"), str) and value.get("arm") in ARMS:
                records.append(value)
    return records


def _copy_ignore(root: Path) -> Callable[[str, list[str]], set[str]]:
    ignored = {".git", ".venv", ".cache", "__pycache__", ".pytest_cache"}
    return lambda _directory, names: {name for name in names if name in ignored or name.startswith("benchmark_records")}


def _git(root: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise OSError("git worktree command failed")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_test_hashes(workspace: Path, hashes: Mapping[str, str]) -> None:
    for relative, expected in hashes.items():
        path = workspace / relative
        if not path.is_file() or _sha256(path) != expected:
            raise _GateFailure("locked test hash changed")


def _read_optional(path: Path) -> str | None:
    return path.read_bytes().decode("utf-8") if path.exists() else None


def _restore_files(workspace: Path, original: Mapping[str, str | None]) -> None:
    for relative, content in original.items():
        target = workspace / relative
        if content is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)


def _call_with_optional_seed(method: Callable[..., Any], messages: list[Mapping[str, str]], seed: int) -> Any:
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        parameters = {}
    if "seed" in parameters or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return method(messages, seed=seed)
    return method(messages)


def _normalise_completion(value: Any) -> ProviderCompletion:
    if isinstance(value, ProviderCompletion):
        return value
    if isinstance(value, str):
        return ProviderCompletion(value)
    if isinstance(value, Mapping):
        text = value.get("text", value.get("content"))
        if not isinstance(text, str):
            raise _GateFailure("provider completion has no text")
        usage = value.get("usage") if isinstance(value.get("usage"), Mapping) else value
        return ProviderCompletion(
            text,
            _usage(usage, "prompt_tokens", "input_tokens", "token_in"),
            _usage(usage, "completion_tokens", "output_tokens", "token_out"),
            value.get("model") if isinstance(value.get("model"), str) else None,
        )
    text = getattr(value, "text", getattr(value, "content", None))
    if isinstance(text, str):
        usage = getattr(value, "usage", None)
        if not isinstance(usage, Mapping):
            usage = value.__dict__ if hasattr(value, "__dict__") else {}
        prompt_tokens = _usage(usage, "prompt_tokens", "input_tokens", "token_in")
        completion_tokens = _usage(usage, "completion_tokens", "output_tokens", "token_out")
        if prompt_tokens is None:
            prompt_tokens = _optional_int_attr(value, "prompt_tokens", "input_tokens", "token_in")
        if completion_tokens is None:
            completion_tokens = _optional_int_attr(value, "completion_tokens", "output_tokens", "token_out")
        return ProviderCompletion(
            text,
            prompt_tokens,
            completion_tokens,
            getattr(value, "model", None) if isinstance(getattr(value, "model", None), str) else None,
        )
    raise _GateFailure("provider returned an unsupported completion type")


def _usage(value: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        item = value.get(key)
        if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            return item
    return None


def _optional_int_attr(value: Any, *names: str) -> int | None:
    for name in names:
        item = getattr(value, name, None)
        if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            return item
    return None


def _sum_usage(attempts: Sequence[_Attempt] | Sequence[ProviderCompletion], field_name: str) -> int | None:
    if not attempts:
        return None
    known = [getattr(item, field_name) for item in attempts if getattr(item, field_name) is not None]
    return sum(int(value) for value in known) if len(known) == len(attempts) else None


def _attempt_record(
    passed: bool,
    usage: Sequence[ProviderCompletion],
    draw: int,
    seed: int,
    failure: str = "",
    *, json_reasks: int | None = None,
) -> _Attempt:
    """Collapse the completions of one draw into a single attempt record."""

    return _Attempt(
        passed=passed,
        prompt_tokens=_sum_usage(usage, "prompt_tokens"),
        completion_tokens=_sum_usage(usage, "completion_tokens"),
        failure=failure,
        draw=draw,
        seed=seed,
        json_reasks=max(0, len(usage) - 1) if json_reasks is None else json_reasks,
    )


def _is_json_failure(exc: _GateFailure) -> bool:
    message = str(exc)
    return any(marker in message for marker in JSON_FAILURE_MARKERS)


def _usage_source(attempts: Sequence[_Attempt], token_in: int | None, token_out: int | None) -> str:
    if token_in is None and token_out is None:
        return "unavailable"
    if all(item.prompt_tokens is not None and item.completion_tokens is not None for item in attempts):
        return "provider"
    return "provider_partial"


def _safe_failure(exc: Exception) -> str:
    if isinstance(exc, BudgetExceeded):
        return str(exc)
    if isinstance(exc, _GateFailure):
        return str(exc)
    if isinstance(exc, ProviderUnavailableError):
        return "provider unavailable"
    if isinstance(exc, BenchmarkError):
        return str(exc)
    return f"{type(exc).__name__} during candidate execution"


def _failure_category(failure: str) -> str:
    """Keep cage repair context categorical and out of hidden-test output."""

    first_line = failure.splitlines()[0].strip() if failure.strip() else ""
    if not first_line:
        return ""
    if ":" in first_line:
        first_line = first_line.split(":", 1)[0]
    return first_line[:200]


def _is_hidden_failure(category: str) -> bool:
    return category.startswith(HIDDEN_GATE_LABEL)


def _invariant_guidance(task: BenchmarkTask) -> str:
    """Restate declared invariants when a hidden gate rejects a candidate."""

    checklist = "\n".join(f"- {invariant}" for invariant in task.invariants)
    if not checklist:
        checklist = "- (the contract declares no explicit invariants; re-read the specification)"
    return (
        "\nVerification Gate Failed: Invariant check or edge-case boundary violation.\n"
        "Ensure your implementation satisfies all declared invariants:\n"
        f"{checklist}\n"
        "Check edge-case handling: duplicate values, empty inputs, boundary ranges, "
        "and explicit exception raising.\n"
    )


def _arm_summary(records: Sequence[Mapping[str, Any]], arm: str) -> dict[str, float | int | None]:
    selected = [record for record in records if record.get("arm") == arm]
    passed = sum(_record_passed(record) for record in selected)
    return {
        "records": len(selected),
        "passed": passed,
        "pass_rate": (passed / len(selected)) if selected else None,
        "mean_attempts": _mean([record.get("attempts") for record in selected]),
        "mean_wall_time": _mean([record.get("wall_time_seconds") for record in selected]),
        "mean_token_in": _mean([record.get("token_in", record.get("tokens_in")) for record in selected]),
        "mean_token_out": _mean([record.get("token_out", record.get("tokens_out")) for record in selected]),
        "mean_budget": _mean([record.get("samples_budget") for record in selected]),
        "mean_drawn": _mean([record.get("samples_drawn", record.get("attempts")) for record in selected]),
        "mean_to_accept": _mean([record.get("samples_to_accept") for record in selected]),
        "json_reasks": sum(int(record.get("json_reasks") or 0) for record in selected),
    }


def _overhead(records: Sequence[Mapping[str, Any]], arm: str, baseline: str) -> dict[str, float | int | None]:
    by_key = {(record.get("task_id"), record.get("arm")): record for record in records}
    time_deltas: list[float] = []
    time_ratios: list[float] = []
    token_deltas: list[float] = []
    for task_id in sorted({record.get("task_id") for record in records}):
        left = by_key.get((task_id, arm))
        right = by_key.get((task_id, baseline))
        if not left or not right:
            continue
        left_time = left.get("wall_time_seconds", left.get("wall_time"))
        right_time = right.get("wall_time_seconds", right.get("wall_time"))
        if isinstance(left_time, (int, float)) and isinstance(right_time, (int, float)):
            time_deltas.append(float(left_time) - float(right_time))
            if right_time:
                time_ratios.append(float(left_time) / float(right_time) - 1.0)
        left_tokens, right_tokens = _total_tokens(left), _total_tokens(right)
        if left_tokens is not None and right_tokens is not None:
            token_deltas.append(float(left_tokens - right_tokens))
    return {
        "n": len(time_deltas),
        "time_seconds": _mean(time_deltas),
        "time_ratio": _mean(time_ratios),
        "tokens": _mean(token_deltas),
    }


def _total_tokens(record: Mapping[str, Any]) -> int | None:
    input_tokens = record.get("token_in", record.get("tokens_in"))
    output_tokens = record.get("token_out", record.get("tokens_out"))
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    return None


def _record_passed(record: Mapping[str, Any]) -> bool:
    value = record.get("pass")
    if value is None:
        value = record.get("passed", record.get("status", False))
    if isinstance(value, str):
        return value.strip().lower() in {"pass", "passed", "complete", "completed", "true", "1"}
    return bool(value)


def _mean(values: Iterable[Any]) -> float | None:
    numeric = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return statistics.mean(numeric) if numeric else None


def _number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _percent(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.1f}%"


def _ci_text(value: Mapping[str, Any]) -> str:
    if value.get("ci95_low") is None:
        return "—"
    return f"[{float(value['ci95_low']):.3f}, {float(value['ci95_high']):.3f}]"


def _wilson_text(passed: Any, total: Any) -> str:
    if not isinstance(passed, int) or not isinstance(total, int) or total <= 0:
        return "—"
    interval = wilson_interval(passed, total)
    if interval is None:
        return "—"
    return f"[{interval[0]:.3f}, {interval[1]:.3f}]"


__all__ = [
    "ARMS",
    "BENCHMARK_VERSION",
    "CAGE_ARMS",
    "DEFAULT_SAMPLES",
    "BenchmarkError",
    "BenchmarkRunner",
    "BenchmarkTask",
    "cage_hurt_cases",
    "paired_pass_rate_difference",
    "read_records",
    "render_report",
    "run_benchmark",
    "wilson_interval",
]


if __name__ == "__main__":
    raise SystemExit(main())
