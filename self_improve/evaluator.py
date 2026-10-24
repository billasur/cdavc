"""Evaluators for the self-improvement loop.

Two implementations, deliberately separated:

- LiveEvaluator: runs the real CD-AVC benchmark on the FIXED task list in
  self_improve/protected/tasks.json and returns MEASURED pass counts and
  token usage. Requires a provider and a token cap; the watchdog threshold
  is set well below the cap (learning: poll-between-bursts overshoot).
- SimulatedEvaluator: deterministic hash-based stub for testing the loop
  mechanics offline. Its scores are SIMULATED - they are never a measurement
  and must never be written into results/ or reported as pass rates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .budget import Budget
from .config import HarnessConfig


@dataclass(frozen=True)
class EvalResult:
    passed: int
    total: int
    tokens: int | None   # None for simulated runs
    simulated: bool


class Evaluator:
    def evaluate(self, config: HarnessConfig) -> EvalResult:
        raise NotImplementedError


class SimulatedEvaluator(Evaluator):
    """Loop-mechanics testing only. NOT a measurement."""

    def __init__(self, total: int = 13) -> None:
        self.total = total

    def evaluate(self, config: HarnessConfig) -> EvalResult:
        digest = hashlib.sha256(config.to_json().encode()).hexdigest()
        passed = int(digest[:4], 16) % (self.total + 1)
        return EvalResult(passed=passed, total=self.total, tokens=None, simulated=True)


class LiveEvaluator(Evaluator):
    """Runs cdavc.BenchmarkRunner on the protected fixed task list. MEASURED."""

    def __init__(self, repo_root: Path, provider, *, token_cap: int, seed: int = 1,
                 results_dir: Path | None = None, budget: Budget | None = None) -> None:
        if token_cap <= 0:
            raise ValueError("LiveEvaluator requires a positive token cap")
        self.repo_root = Path(repo_root)
        self.provider = provider
        # Watchdog threshold well under the cap: a burst can cross between polls.
        self.token_cap = token_cap
        self.seed = seed
        self.budget = budget
        spec = json.loads((Path(__file__).parent / "protected" / "tasks.json").read_text())
        self.benchmark_root = self.repo_root / spec["benchmark_root"]
        self.arm = spec["arm"]
        self.task_ids = list(spec["task_ids"])
        self.results_dir = Path(results_dir) if results_dir else (
            self.repo_root / "self_improve" / "runs")

    def evaluate(self, config: HarnessConfig) -> EvalResult:
        if self.budget is not None:
            self.budget.check_can_start(f"evaluation (seed {self.seed})")
        import sys
        sys.path.insert(0, str(self.repo_root / "src"))
        from cdavc.benchmark import BenchmarkRunner, BenchmarkTask  # noqa: PLC0415

        tasks = []
        rel_root = self.benchmark_root.relative_to(self.repo_root)
        for tid in self.task_ids:
            spec_path = self.benchmark_root / tid / "spec.json"
            spec = dict(json.loads(spec_path.read_text()))
            task_dir = (rel_root / tid).as_posix()
            impl = spec["implementation_files"]
            sol_name = Path(impl[0]).name
            spec["implementation_files"] = [
                i if Path(i).is_absolute() or i.startswith(task_dir) else f"{task_dir}/{i}"
                for i in impl
            ]
            spec["test_files"] = [f"{task_dir}/public_tests.py",
                                  f"{task_dir}/hidden_tests.py",
                                  f"{task_dir}/regression_tests.py"]
            spec["test_command"] = ("python", f"{task_dir}/public_tests.py", sol_name)
            spec["hidden_test_command"] = ("python", f"{task_dir}/hidden_tests.py", sol_name)
            spec["regression_command"] = ("python", f"{task_dir}/regression_tests.py", sol_name)
            tasks.append(BenchmarkTask.from_dict(spec))
        run_dir = self.results_dir / f"seed{self.seed}"
        run_dir.mkdir(parents=True, exist_ok=True)
        records = run_dir / (hashlib.sha256(config.to_json().encode()).hexdigest()[:12] + ".jsonl")
        runner = BenchmarkRunner(
            self.repo_root,
            provider=self.provider,
            tasks=tasks,
            records_path=records,
            seed=self.seed,
            model=getattr(self.provider, "model", None),
            arms=(self.arm,),
            **config.to_runner_kwargs(),
        )
        runner.run()
        passed = 0
        tokens = 0
        for line in records.read_text().splitlines():
            record = json.loads(line)
            if record.get("arm") != self.arm:
                continue
            if record.get("passed"):
                passed += 1
            tokens += (record.get("token_in") or 0) + (record.get("token_out") or 0)
        if self.budget is not None:
            self.budget.charge(tokens, f"evaluation (seed {self.seed})")
        return EvalResult(passed=passed, total=len(tasks), tokens=tokens, simulated=False)
