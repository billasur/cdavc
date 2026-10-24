"""The self-improvement controller: propose -> evaluate -> keep or roll back.

Hard rules encoded here (not just documented):
1. The evaluator is fixed. Before every iteration the controller checks that
   self_improve/protected/ and benchmarks_dev2/ and benchmarks_heldout/ are
   clean against git HEAD; a dirty evaluator aborts the loop.
2. Only self_improve/harness_config.json is mutated by the loop, and only
   through HarnessConfig validation, so the editable surface cannot widen.
3. Keep-if-better compares MEASURED pass counts on the fixed task list,
   tie-break on fewer tokens. Simulated scores are never kept as improvements.
4. Every iteration is appended to self_improve/IMPROVE_LOG.md and labelled
   "measured" or "simulated (mechanics only)".
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config import HarnessConfig
from .evaluator import Evaluator, EvalResult
from .proposer import Proposer

IST = timezone(timedelta(hours=5, minutes=30))

PROTECTED_PATHS = ("self_improve/protected", "benchmarks_dev2", "benchmarks_heldout")
CONFIG_PATH = "self_improve/harness_config.json"
LOG_PATH = "self_improve/IMPROVE_LOG.md"


class EvaluatorTamperedError(RuntimeError):
    """Protected evaluation files differ from git HEAD."""


@dataclass
class LoopState:
    best_config: HarnessConfig
    best_result: EvalResult | None = None
    tried: list[HarnessConfig] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


def check_evaluator_clean(repo_root: Path) -> None:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *PROTECTED_PATHS],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.strip()
    if dirty:
        raise EvaluatorTamperedError(
            "protected evaluation files differ from git HEAD; refusing to run:\n" + dirty
        )


def is_better(candidate: EvalResult, best: EvalResult | None) -> bool:
    if best is None:
        return True
    if candidate.passed != best.passed:
        return candidate.passed > best.passed
    if candidate.tokens is not None and best.tokens is not None:
        return candidate.tokens < best.tokens
    return False


class Controller:
    def __init__(self, repo_root: Path, proposer: Proposer, evaluator: Evaluator) -> None:
        self.repo_root = Path(repo_root)
        self.proposer = proposer
        self.evaluator = evaluator
        self.config_file = self.repo_root / CONFIG_PATH
        self.log_file = self.repo_root / LOG_PATH

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo_root, check=True,
                       capture_output=True, text=True)

    def _write_config(self, config: HarnessConfig) -> None:
        config.validate()
        self.config_file.write_text(config.to_json())

    def _append_log(self, line: str) -> None:
        if not self.log_file.exists():
            self.log_file.write_text(
                "# Self-improvement log\n\n"
                "Each row: time (IST), config, score, kept?, label. "
                "'simulated' rows test loop mechanics only and are NOT measurements.\n\n"
            )
        with self.log_file.open("a") as fh:
            fh.write(line + "\n")

    def run(self, iterations: int) -> LoopState:
        check_evaluator_clean(self.repo_root)
        current = HarnessConfig.load(self.config_file)
        state = LoopState(best_config=current, tried=[current])
        for _ in range(iterations):
            candidate = self.proposer.propose(current, state.tried, state.history)
            if candidate is None:
                break
            check_evaluator_clean(self.repo_root)
            self._write_config(candidate)
            result = self.evaluator.evaluate(candidate)
            label = "simulated (mechanics only)" if result.simulated else "measured"
            keep = (not result.simulated) and is_better(result, state.best_result)
            state.tried.append(candidate)
            state.history.append({"config": candidate.to_runner_kwargs(),
                                  "passed": result.passed, "total": result.total,
                                  "tokens": result.tokens, "kept": keep,
                                  "simulated": result.simulated})
            now = datetime.now(IST).strftime("%H:%M")
            compact = json.dumps(candidate.to_runner_kwargs(), sort_keys=True)
            self._append_log(
                f"- {now} - `{compact}` - "
                f"{result.passed}/{result.total}"
                + (f", {result.tokens} tokens" if result.tokens is not None else "")
                + f" - {'KEPT' if keep else 'rolled back'} - {label}"
            )
            if keep:
                state.best_config = candidate
                state.best_result = result
                current = candidate
                self._git("add", CONFIG_PATH, LOG_PATH)
                self._git("commit", "-m",
                          f"self-improve: keep {compact} "
                          f"({result.passed}/{result.total} {label})")
            else:
                # roll back: restore the incumbent config content
                self._write_config(current)
        return state
