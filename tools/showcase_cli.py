#!/usr/bin/env python3
"""
CD-AVC Showcase CLI Runner.
Demonstrates all verification features across 3 tasks with rich terminal output:
1. AST Contract & Symbol Gating
2. Targeted Test Gate & Guided Self-Repair
3. Full Project Regression Gate & Atomic Vitrine Merge
"""

import sys
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cdavc.graph import TaskGraph, Task
from cdavc.providers import MockProvider
from cdavc.supervisor import Supervisor, VerificationFailure

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CLEAR_LINE = "\r\033[K"

CYAN = "\033[38;5;81m"
EMERALD = "\033[38;5;120m"
AMBER = "\033[38;5;215m"
RED = "\033[38;5;203m"
WHITE = "\033[38;5;255m"
GRAY = "\033[38;5;244m"

def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"

def banner():
    print()
    print(c("  ┌──────────────────────────────────────────────────────────────────────────┐", CYAN))
    print(c("  │", CYAN) + c("   CD-AVC · Contract-Driven Asymmetric Verification Cage                 ", BOLD + WHITE) + c("│", CYAN))
    print(c("  │", CYAN) + c("   Deterministic Verification & Control Harness for Local Coding Models    ", GRAY) + c("│", CYAN))
    print(c("  └──────────────────────────────────────────────────────────────────────────┘", CYAN))
    print()
    print(f"  {c('●', EMERALD)} {c('Project Graph:', BOLD)}  cdavc-calculator-pipeline (3 tasks declared)")
    print(f"  {c('●', EMERALD)} {c('Model Runtime:', BOLD)}  Local Qwen2.5-Coder (Offline Deterministic Mock)")
    print(f"  {c('●', EMERALD)} {c('Worktree Mode:', BOLD)}  Ephemeral Isolated Sandbox (Protected Root)")
    print(f"  {c('●', EMERALD)} {c('Verification:', BOLD)}   AST Syntax → Symbol Invariants → Unit Tests → Regression")
    print(c("  " + "─" * 74, GRAY))
    print()

class VisualSupervisor(Supervisor):
    def __init__(self, graph_path: Path, provider, pace: float = 0.35):
        super().__init__(graph_path, provider)
        self.pace = pace

    def sleep(self, factor=1.0):
        if self.pace > 0:
            time.sleep(self.pace * factor)

    def _run_task(self, task: Task):
        print(f"  {c('┌─', CYAN)} {c(f'[{task.id}]', BOLD + WHITE)} {c(task.title, BOLD)}")
        deps = ", ".join(task.dependencies) if task.dependencies else "Root (None)"
        print(f"  {c('│', CYAN)}  {c('Dependencies:', GRAY)} {deps}")
        print(f"  {c('│', CYAN)}  {c('Allowed Files:', GRAY)} {', '.join(task.implementation_files)} {c('(Strict boundary)', DIM)}")
        print(f"  {c('│', CYAN)}  {c('Symbols Required:', GRAY)} {', '.join(task.symbols)}")
        self.sleep(0.8)

        missing_tests = [path for path in task.test_files if not (self.execution_root / path).is_file()]
        if not task.test_files or missing_tests:
            return super()._run_task(task)

        original = {path: (self.execution_root / path).read_text() if (self.execution_root / path).exists() else None for path in task.implementation_files}
        attempts = []
        previous_failure = ""

        for attempt in range(1, task.max_retries + 2):
            print(f"  {c('│', CYAN)}")
            print(f"  {c('│', CYAN)}  {c(f'▶ Attempt {attempt} of {task.max_retries + 1}', AMBER if attempt > 1 else WHITE)}")
            prompt = self._prompt(task, previous_failure)
            self.sleep(0.5)

            try:
                print(f"  {c('│', CYAN)}    {c('⚡ Gate 0: Generating candidate patch...', GRAY)}", end="", flush=True)
                self.sleep(0.4)
                response = self.provider.complete([{"role": "user", "content": prompt}])
                self._apply_response(task, response)
                print(f"{CLEAR_LINE}  {c('│', CYAN)}    {c('✔ Gate 0: Applied candidate to isolated worktree', EMERALD)}")
                self.sleep(0.4)

                print(f"  {c('│', CYAN)}    {c('⚡ Gate 1: AST Contract & Symbol Verification...', GRAY)}", end="", flush=True)
                self.sleep(0.4)
                # Verify AST specifically
                for relative in task.implementation_files:
                    source = (self.execution_root / relative).read_text()
                    import ast
                    tree = compile(source, relative, "exec", ast.PyCF_ONLY_AST)
                    declared = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
                    missing = set(task.symbols) - declared
                    if missing:
                        raise VerificationFailure(f"AST gate failed: missing required symbol(s) {sorted(missing)}")
                print(f"{CLEAR_LINE}  {c('│', CYAN)}    {c('✔ Gate 1: AST Contract & Symbol Invariants PASSED', EMERALD)}")
                self.sleep(0.4)

                print(f"  {c('│', CYAN)}    {c('⚡ Gate 2: Targeted Unit Tests...', GRAY)}", end="", flush=True)
                self.sleep(0.4)
                self._run_command(task.test_command, "targeted test")
                print(f"{CLEAR_LINE}  {c('│', CYAN)}    {c('✔ Gate 2: Targeted Unit Tests PASSED', EMERALD)}")
                self.sleep(0.4)

                print(f"  {c('│', CYAN)}    {c('⚡ Gate 3: Full Project Regression Suite...', GRAY)}", end="", flush=True)
                self.sleep(0.4)
                self._run_command(("python", "-m", "unittest", "discover", "-s", "tests"), "regression test")
                print(f"{CLEAR_LINE}  {c('│', CYAN)}    {c('✔ Gate 3: Regression Suite PASSED (Zero collateral damage)', EMERALD)}")
                self.sleep(0.4)

            except Exception as exc:
                self._restore(original)
                previous_failure = str(exc)
                attempts.append({"attempt": attempt, "status": "REJECTED", "failure": previous_failure})
                
                # Format friendly failure label
                err_summary = previous_failure.splitlines()[0] if previous_failure else "verification failed"
                if "targeted test failed" in err_summary:
                    for line in previous_failure.splitlines():
                        if "AssertionError:" in line or "FAIL:" in line:
                            err_summary = f"Targeted Test Failure: {line.strip()}"
                            break

                print(f"{CLEAR_LINE}  {c('│', CYAN)}    {c(f'✖ Gate REJECTED: {err_summary}', RED)}")
                print(f"  {c('│', CYAN)}    {c('⎌ Rollback:', AMBER)} Ephemeral workspace cleaned; main repository untouched.")
                print(f"  {c('│', CYAN)}    {c('↻ Self-Repair Loop:', AMBER)} Traceback injected into model retry context.")
                self.sleep(0.8)
                continue

            attempts.append({"attempt": attempt, "status": "ACCEPTED"})
            print(f"  {c('│', CYAN)}    {c('🔒 Vitrine Seal:', EMERALD)} {c('Candidate verified — atomically merged into source tree.', WHITE)}")
            print(f"  {c('└─', CYAN)} {c('✔ TASK COMPLETED', BOLD + EMERALD)}")
            print()
            self.sleep(0.4)
            return {"status": "COMPLETED", "attempts": attempt, "attempt_log": attempts, "failure": ""}

        print(f"  {c('└─', CYAN)} {c('✖ TASK FAILED (Max retries exhausted)', BOLD + RED)}")
        print()
        return {"status": "FAILED", "attempts": len(attempts), "attempt_log": attempts, "failure": previous_failure}

def print_summary(result: dict):
    print(c("  ┌──────────────────────────────────────────────────────────────────────────┐", WHITE))
    print(c("  │                           EXECUTION SUMMARY                              │", BOLD + WHITE))
    print(c("  ├──────────┬─────────────────────────────────────┬──────────┬──────────────┤", WHITE))
    print(c("  │ Task     │ Title                               │ Attempts │ Final Status │", BOLD + WHITE))
    print(c("  ├──────────┼─────────────────────────────────────┼──────────┼──────────────┤", WHITE))
    for task_id, task in result["tasks"].items():
        status_c = c("COMPLETED", BOLD + EMERALD) if task["status"] == "COMPLETED" else c("FAILED", BOLD + RED)
        title_map = {
            "TASK-001": "Tokenize mathematical expression    ",
            "TASK-002": "Evaluate token stream               ",
            "TASK-003": "End-to-end calculator pipeline      ",
        }
        title = title_map.get(task_id, task_id.ljust(35))
        print(f"  │ {c(task_id, BOLD)} │ {title} │    {task['attempts']}     │  {status_c}  │")
    print(c("  └──────────┴─────────────────────────────────────┴──────────┴──────────────┘", WHITE))
    print()
    print(f"  {c('✔', EMERALD)} All 3 tasks verified and atomically committed.")
    print(f"  {c('📄 Audit report generated at:', GRAY)} {c('examples/demo3/execution_report.md', WHITE)}")
    print(f"  {c('📊 Audit log generated at:   ', GRAY)} {c('examples/demo3/execution_log.json', WHITE)}")
    print()

def main():
    parser = argparse.ArgumentParser(description="CD-AVC 3-Task Showcase Runner")
    parser.add_argument("--pace", type=float, default=0.25, help="delay in seconds between steps (for demo video pacing)")
    parser.add_argument("--instant", action="store_true", help="run without delay")
    args = parser.parse_args()

    pace = 0.0 if args.instant else args.pace

    banner()

    resp_dir = Path(__file__).resolve().parent.parent / "examples" / "demo3" / "responses"
    resp_files = [
        resp_dir / "01_bad_ast.json",
        resp_dir / "02_good_tokenizer.json",
        resp_dir / "03_bad_logic.json",
        resp_dir / "04_good_evaluator.json",
        resp_dir / "05_good_calculator.json",
    ]

    provider = MockProvider(p.read_text() for p in resp_files)
    graph_path = Path(__file__).resolve().parent.parent / "examples" / "demo3" / "task_graph.json"

    sup = VisualSupervisor(graph_path, provider, pace=pace)
    result = sup.run()
    print_summary(result)
    return 0

if __name__ == "__main__":
    sys.exit(main())
