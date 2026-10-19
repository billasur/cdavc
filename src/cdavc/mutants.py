"""Hand-mutant kill rate for held-out hidden tests (experiment 4).

Deterministic, stdlib-only mutation harness. For each held-out task it
generates single-site mutants of ``reference_solution.py`` with a small set
of hand-picked AST operators (off-by-one constants, comparison swaps,
negated conditions, arithmetic swaps), then runs the task's
``hidden_tests.py`` against each mutant in a subprocess.

A mutant is "killed" when the hidden tests exit non-zero or time out, and
"survives" when they exit zero. The kill rate (killed / viable mutants) is a
test-adequacy number for the held-out set, in the spirit of TestGen-LLM and
the mutation-guided test-generation work at Meta: a test suite only earns
trust if it rejects small, deliberate behaviour changes.

Usage:
    python -m cdavc.mutants [--root benchmarks_heldout] [--timeout 10]
                            [--max-mutants N] [--out report.json]

No LLM is involved and no model is benchmarked here; the output is a
property of the test suites only.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# Comparison swaps: off-by-one at the boundary (Lt<->LtE, Gt<->GtE) and
# equality inversion (Eq<->NotEq). Only single-operand comparisons mutate.
_COMPARE_SWAPS = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}

# Arithmetic swaps kept type-conservative: Add<->Sub, Mult<->FloorDiv.
_ARITH_SWAPS = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
}


@dataclass(frozen=True)
class Mutant:
    """One single-site mutation of a reference solution."""

    mutant_id: str
    operator: str
    lineno: int
    detail: str
    source: str


def _describe(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 - the description is cosmetic only
        return type(node).__name__


@dataclass(frozen=True)
class _Site:
    operator: str  # "compare_swap" | "arith_swap" | "const_shift" | "negate_test"
    ordinal: int  # index within that operator family, pre-order
    lineno: int
    detail: str
    delta: int = 0  # +1 / -1 for const_shift


def _enumerate_sites(tree: ast.Module) -> list[_Site]:
    """List every mutable site, pre-order, per-operator-family ordinals."""
    sites: list[_Site] = []
    counters = {"compare_swap": 0, "arith_swap": 0, "const_shift": 0, "negate_test": 0}

    class Finder(ast.NodeVisitor):
        def visit_Compare(self, node: ast.Compare) -> None:
            if len(node.ops) == 1 and type(node.ops[0]) in _COMPARE_SWAPS:
                sites.append(_Site("compare_swap", counters["compare_swap"], node.lineno, _describe(node)))
                counters["compare_swap"] += 1
            self.generic_visit(node)

        def visit_BinOp(self, node: ast.BinOp) -> None:
            if type(node.op) in _ARITH_SWAPS:
                sites.append(_Site("arith_swap", counters["arith_swap"], node.lineno, _describe(node)))
                counters["arith_swap"] += 1
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, int) and not isinstance(node.value, bool):
                for delta in (1, -1):
                    sites.append(
                        _Site("const_shift", counters["const_shift"], node.lineno, _describe(node), delta)
                    )
                counters["const_shift"] += 1

        def visit_If(self, node: ast.If) -> None:
            sites.append(_Site("negate_test", counters["negate_test"], node.lineno, "if " + _describe(node.test)))
            counters["negate_test"] += 1
            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            sites.append(
                _Site("negate_test", counters["negate_test"], node.lineno, "while " + _describe(node.test))
            )
            counters["negate_test"] += 1
            self.generic_visit(node)

    Finder().visit(tree)
    return sites


class _ApplyOne(ast.NodeTransformer):
    """Applies one site to a fresh tree, counting pre-order like the finder."""

    def __init__(self, site: _Site):
        self.site = site
        self.count = -1

    def _hit(self) -> bool:
        self.count += 1
        return self.count == self.site.ordinal

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        if self.site.operator == "compare_swap" and len(node.ops) == 1 and type(node.ops[0]) in _COMPARE_SWAPS:
            if self._hit():
                node.ops[0] = _COMPARE_SWAPS[type(node.ops[0])]()
        self.generic_visit(node)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        if self.site.operator == "arith_swap" and type(node.op) in _ARITH_SWAPS:
            if self._hit():
                node.op = _ARITH_SWAPS[type(node.op)]()
        self.generic_visit(node)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self.site.operator == "const_shift" and isinstance(node.value, int) and not isinstance(node.value, bool):
            if self._hit():
                node.value = node.value + self.site.delta
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        if self.site.operator == "negate_test" and self._hit():
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        self.generic_visit(node)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        if self.site.operator == "negate_test" and self._hit():
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        self.generic_visit(node)
        return node


def generate_mutants(source: str) -> list[Mutant]:
    """Generate all single-site mutants of ``source``.

    Deterministic: the same input always yields the same list. Mutants whose
    unparsed source duplicates the original or an earlier mutant are dropped,
    as are mutants that fail to compile.
    """
    tree = ast.parse(source)
    mutants: list[Mutant] = []
    seen = {source}
    for site in _enumerate_sites(tree):
        new_tree = copy.deepcopy(tree)
        _ApplyOne(site).visit(new_tree)
        ast.fix_missing_locations(new_tree)
        try:
            mutated = ast.unparse(new_tree)
            compile(mutated, "<mutant>", "exec")
        except (SyntaxError, ValueError):
            continue
        if mutated in seen:
            continue
        seen.add(mutated)
        mutants.append(
            Mutant(
                mutant_id=f"m{len(mutants):04d}",
                operator=site.operator,
                lineno=site.lineno,
                detail=site.detail if not site.delta else f"{site.detail} {'+' if site.delta > 0 else '-'} 1",
                source=mutated,
            )
        )
    return mutants


def wilson_interval(killed: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if total == 0:
        return (0.0, 1.0)
    p = killed / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = (z / denom) * ((p * (1 - p) / total) + z * z / (4 * total * total)) ** 0.5
    return (max(0.0, centre - margin), min(1.0, centre + margin))


@dataclass
class MutantOutcome:
    mutant_id: str
    operator: str
    lineno: int
    detail: str
    status: str  # "killed" | "survived" | "timeout"
    seconds: float


@dataclass
class TaskResult:
    task_id: str
    reference_passes: bool
    mutants_total: int
    killed: int
    survived: int
    timeouts: int
    kill_rate: float | None
    wilson95: tuple[float, float] | None
    outcomes: list[MutantOutcome] = field(default_factory=list)


def _run_hidden_tests(task_dir: Path, solution: Path, timeout: float) -> tuple[int, float]:
    """Run hidden_tests.py against ``solution``; return (exit_code, seconds).

    Exit code -1 marks a timeout. Every held-out evaluator accepts an
    explicit solution path as argv[1] and exits 0 on pass, non-zero on
    failure, so a timeout counts as killed (the suite rejects by hanging,
    which the benchmark runner would also treat as a failure).
    """
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(task_dir / "hidden_tests.py"), str(solution)],
            capture_output=True,
            timeout=timeout,
        )
        return proc.returncode, time.monotonic() - start
    except subprocess.TimeoutExpired:
        return -1, time.monotonic() - start


def run_task(task_dir: Path, timeout: float = 10.0, max_mutants: int | None = None) -> TaskResult:
    """Compute the hidden-test mutant kill rate for one held-out task."""
    task_id = task_dir.name
    reference = task_dir / "reference_solution.py"
    reference_source = reference.read_text(encoding="utf-8")

    code, _ = _run_hidden_tests(task_dir, reference, timeout)
    if code != 0:
        return TaskResult(task_id, False, 0, 0, 0, 0, None, None, [])

    mutants = generate_mutants(reference_source)
    if max_mutants is not None and len(mutants) > max_mutants:
        # Deterministic stride subsample keeps the operator mix; no seed.
        step = len(mutants) / max_mutants
        mutants = [mutants[int(i * step)] for i in range(max_mutants)]

    outcomes: list[MutantOutcome] = []
    with tempfile.TemporaryDirectory(prefix="cdavc_mutants_") as tmp:
        for mutant in mutants:
            mutant_path = Path(tmp) / f"{mutant.mutant_id}.py"
            mutant_path.write_text(mutant.source, encoding="utf-8")
            code, seconds = _run_hidden_tests(task_dir, mutant_path, timeout)
            if code == -1:
                status = "timeout"
            elif code == 0:
                status = "survived"
            else:
                status = "killed"
            outcomes.append(
                MutantOutcome(mutant.mutant_id, mutant.operator, mutant.lineno, mutant.detail, status, seconds)
            )

    killed = sum(1 for o in outcomes if o.status in ("killed", "timeout"))
    timeouts = sum(1 for o in outcomes if o.status == "timeout")
    survived = sum(1 for o in outcomes if o.status == "survived")
    total = len(outcomes)
    rate = (killed / total) if total else None
    interval = wilson_interval(killed, total) if total else None
    return TaskResult(task_id, True, total, killed, survived, timeouts, rate, interval, outcomes)


def run_all(root: Path, timeout: float = 10.0, max_mutants: int | None = None) -> list[TaskResult]:
    """Run every held-out task under ``root`` (agentN/task_* directories)."""
    task_dirs = sorted(p for p in root.glob("agent*/*") if (p / "hidden_tests.py").exists())
    return [run_task(d, timeout=timeout, max_mutants=max_mutants) for d in task_dirs]


def _result_to_dict(r: TaskResult) -> dict:
    return {
        "task_id": r.task_id,
        "reference_passes": r.reference_passes,
        "mutants_total": r.mutants_total,
        "killed": r.killed,
        "survived": r.survived,
        "timeouts": r.timeouts,
        "kill_rate": r.kill_rate,
        "wilson95": list(r.wilson95) if r.wilson95 else None,
        "surviving_mutants": [
            {"mutant_id": o.mutant_id, "operator": o.operator, "lineno": o.lineno, "detail": o.detail}
            for o in r.outcomes
            if o.status == "survived"
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default="benchmarks_heldout", help="held-out tasks root")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds per test run")
    parser.add_argument("--max-mutants", type=int, default=None, help="cap mutants per task (stride subsample)")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    args = parser.parse_args(argv)

    results = run_all(Path(args.root), timeout=args.timeout, max_mutants=args.max_mutants)
    total_mutants = sum(r.mutants_total for r in results)
    total_killed = sum(r.killed for r in results)
    skipped = [r.task_id for r in results if not r.reference_passes]

    for r in results:
        if r.kill_rate is None:
            print(f"{r.task_id}: SKIPPED (reference does not pass hidden tests)")
        else:
            lo, hi = r.wilson95
            print(
                f"{r.task_id}: kill rate {r.killed}/{r.mutants_total} "
                f"= {r.kill_rate:.3f} (95% Wilson CI [{lo:.3f}, {hi:.3f}]), "
                f"survived {r.survived}, timeouts {r.timeouts}"
            )
    if total_mutants:
        lo, hi = wilson_interval(total_killed, total_mutants)
        print(
            f"OVERALL: {total_killed}/{total_mutants} = {total_killed / total_mutants:.3f} "
            f"(95% Wilson CI [{lo:.3f}, {hi:.3f}])"
        )

    report = {
        "status": "mutation kill rate of the test suites; no model benchmarked",
        "root": args.root,
        "timeout_seconds": args.timeout,
        "max_mutants_per_task": args.max_mutants,
        "tasks": [_result_to_dict(r) for r in results],
        "overall": {
            "mutants": total_mutants,
            "killed": total_killed,
            "kill_rate": (total_killed / total_mutants) if total_mutants else None,
            "wilson95": list(wilson_interval(total_killed, total_mutants)) if total_mutants else None,
            "skipped_tasks": skipped,
        },
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
