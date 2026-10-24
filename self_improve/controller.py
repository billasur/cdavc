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

from .budget import BudgetExhausted
from .config import HarnessConfig
from .evaluator import Evaluator, EvalResult
from .manifest import verify_manifest, ManifestMismatchError
from .proposer import Proposer

IST = timezone(timedelta(hours=5, minutes=30))

CONFIG_PATH = "self_improve/harness_config.json"
LOG_PATH = "self_improve/IMPROVE_LOG.md"

# A single-seed keep is a MECHANICAL keep, nothing more: run-to-run noise at
# t=0.7 was previously measured to be as large as arm differences. A keep
# confirmed on VALIDATION_SEEDS is logged as a "multi-seed observed gain
# under this protocol" - small N, selected on the dev2 set, NOT a validated
# research result. Validation re-runs cost tokens too; they are charged to
# the same budget as the search itself.
VALIDATION_SEEDS = (2, 3)


class EvaluatorTamperedError(RuntimeError):
    """Protected evaluation files differ from the pinned manifest."""


@dataclass
class LoopState:
    best_config: HarnessConfig
    best_result: EvalResult | None = None
    tried: list[HarnessConfig] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    validated: bool = False


def check_evaluator_clean(repo_root: Path) -> None:
    try:
        verify_manifest(repo_root)
    except ManifestMismatchError as exc:
        raise EvaluatorTamperedError(str(exc)) from exc


def is_better(candidate: EvalResult, best: EvalResult | None) -> bool:
    """Equal-cost comparison: a config that retries more is not 'better' for
    passing more if it also spent more total compute to get there."""
    if best is None:
        return True
    if candidate.tokens is not None and best.tokens is not None:
        if candidate.passed > best.passed and candidate.tokens <= best.tokens:
            return True
        if candidate.passed == best.passed and candidate.tokens < best.tokens:
            return True
        return False
    # Token counts unknown: only a strict pass improvement can be compared.
    return candidate.passed > best.passed


class Controller:
    def __init__(self, repo_root: Path, proposer: Proposer, evaluator: Evaluator,
                 evaluator_for_seed: "callable[[int], Evaluator] | None" = None) -> None:
        self.repo_root = Path(repo_root)
        self.proposer = proposer
        self.evaluator = evaluator
        # When provided, a measured keep is immediately re-checked on
        # VALIDATION_SEEDS; only then is it logged as a validated gain.
        self.evaluator_for_seed = evaluator_for_seed
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

    def _validate_gain(self, candidate: HarnessConfig, result: EvalResult,
                       state: LoopState, label: str) -> bool:
        """Re-run candidate and incumbent on the validation seeds. The keep
        stands only if the candidate wins the equal-cost comparison on every
        validation seed too. Otherwise it was single-seed noise: roll back."""
        assert self.evaluator_for_seed is not None
        incumbent = state.best_config
        for seed in VALIDATION_SEEDS:
            evaluator = self.evaluator_for_seed(seed)
            cand = evaluator.evaluate(candidate)
            base = evaluator.evaluate(incumbent)
            check_evaluator_clean(self.repo_root)
            self._append_log(
                f"- {datetime.now(IST).strftime('%H:%M')} - validation seed {seed}: "
                f"candidate {cand.passed}/{cand.total} ({cand.tokens} tok) vs "
                f"incumbent {base.passed}/{base.total} ({base.tokens} tok)"
            )
            if not is_better(cand, base):
                return False
        return True

    def run(self, iterations: int) -> LoopState:
        check_evaluator_clean(self.repo_root)
        current = HarnessConfig.load(self.config_file)
        state = LoopState(best_config=current, tried=[current])
        for _ in range(iterations):
            try:
                candidate = self.proposer.propose(current, state.tried, state.history)
            except BudgetExhausted as exc:
                self._append_log(f"- {datetime.now(IST).strftime('%H:%M')} - STOPPED: {exc}")
                break
            if candidate is None:
                break
            check_evaluator_clean(self.repo_root)
            self._write_config(candidate)
            try:
                result = self.evaluator.evaluate(candidate)
            except BudgetExhausted as exc:
                self._write_config(current)  # restore incumbent
                self._append_log(f"- {datetime.now(IST).strftime('%H:%M')} - STOPPED: {exc}")
                break
            check_evaluator_clean(self.repo_root)  # catch mid-run edits
            label = "simulated (mechanics only)" if result.simulated else "measured (single-seed, provisional)"
            keep = (not result.simulated) and is_better(result, state.best_result)
            if keep and result.tokens is not None and self.evaluator_for_seed is not None:
                keep = self._validate_gain(candidate, result, state, label)
                if keep:
                    label = ("multi-seed observed gain under this protocol, seeds 1,"
                             + ",".join(str(s) for s in VALIDATION_SEEDS)
                             + " (small N, dev2-selected, not a validated research result)")
                    state.validated = True
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
