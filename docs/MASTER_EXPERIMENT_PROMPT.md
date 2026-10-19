# Master Engineering Prompt: CD-AVC Empirical Optimization & Edge-Case Resilience

> **Context**: This master prompt encapsulates empirical findings from the 20-task local model benchmark (`Qwen2.5-7B-Instruct` on Apple Silicon) comparing `baseline_single`, `baseline_retry`, and `cdavc`. It outlines the exact architecture gaps identified and provides an executable phased plan to advance CD-AVC's accuracy, quality, and edge-case resilience.

---

## Part 1: Empirical Baseline & Ground Truth Findings

### Measured Performance (20 Fixed Tasks, Qwen 2.5 7B Q4_K_M)
- **`baseline_single`**: 60.0% pass rate (12/20) · Mean wall time: 10.25s · Mean input tokens: 167.0 tok
- **`baseline_retry`**: 90.0% pass rate (18/20) · Mean wall time: 16.17s · Mean input tokens: 239.2 tok
- **`cdavc` (cage)**: **85.0% pass rate (17/20)** · Mean wall time: **16.44s** · Mean input tokens: **230.5 tok**
- **Paired Pass-Rate Gain**: **+25.0 percentage points** over single-shot (95% CI `[0.055, 0.445]`, strictly positive).
- **Cage Overhead vs Plain Retry**: **+0.272s** (+1.7% wall clock overhead) for full ephemeral git worktree isolation, AST parsing, SHA-256 test integrity locking, and regression test execution.
- **Context Efficiency**: CD-AVC used **3.6% fewer input prompt tokens** than plain retry by avoiding 4000-character stack trace dumps.
- **Cage-Hurt Rate**: **0.0%** (0 false rejections of valid code).

### Critical Vulnerabilities Uncovered in Baselines
1. **The Test-Leakage Fallacy**: `baseline_retry` achieves 90% only because the harness dumps the **held-out/hidden test assertions directly into the model's repair prompt** (e.g. in `task_006`: `expected [-3, -2, 0, 0, 4, 9], got [-3, -2, 0, 4, 9]`). In production, hidden test oracles do not exist; plain retry is overfitted to leaked answers.
2. **Zero Regression & Integrity Protection**: `baseline_retry` never runs regression tests across the repository, does not check AST symbols, and does not detect test tampering. If a model modifies `tests/test_*.py` or breaks sibling files, baseline accepts it as a PASS.

### Analysis of the 3 CD-AVC Failure Cases
1. **`task_006` (Merge Sorted Lists - Duplicates)**: The model assumed sorted lists must contain distinct elements and deduplicated them (`[-3, -2, 0, 4, 9]` instead of `[-3, -2, 0, 0, 4, 9]`). The public test had no duplicates, so it passed. The hidden test failed categorically, but CD-AVC provided no semantic guidance about duplicate preservation.
2. **`task_013` (Camel to Snake - Acronym Runs)**: The model failed on `"HTTPRequest"` -> `"http_request"`. `baseline_retry` passed because it was fed the literal string `"http_request"`. `cdavc` failed because it suppressed the failure output of the **public/targeted test** during retries.
3. **`task_015` (Roman to Integer - Canonical Validation)**: The invariant required `Raise ValueError for empty, non-canonical or out-of-range numerals` (e.g. `"IIII"`). The model output a naive lookup adder without validation. Neither baseline nor CD-AVC could repair this without guidance.

---

## Part 2: CD-AVC Architecture Upgrade Objectives

You are tasked with upgrading the CD-AVC verification cage and benchmark harness across four concrete capabilities:

### Objective 1: Differentiate Public Diagnostics from Hidden Test Privacy
- **Problem**: CD-AVC currently sets `include_output=False` on *all* cage gates, including public targeted tests.
- **Solution**:
  - For **Targeted / Public Tests** (Gate 3) and **Regression Tests** (Gate 4): These are public repository assets. When they fail, capture stdout/stderr and format a clean diagnostic traceback (without leaking workspace absolute paths) so the model has the exact debugging signal a human engineer has.
  - For **Held-Out / Hidden Tests**: Preserve strict zero-leakage privacy. Never expose hidden assertions, secret strings, or expected outputs.

### Objective 2: Invariant-Anchored Semantic Guidance on Hidden Failure
- **Problem**: When a hidden gate fails, the model receives only `Previous deterministic failure category: hidden_test_failure`, giving it zero direction on edge cases.
- **Solution**:
  - When Gate 3 (Hidden) fails, dynamically extract the task's declared `invariants` from the contract and synthesize structured edge-case remediation guidance into the repair prompt:
    ```text
    Verification Gate Failed: Invariant check or edge-case boundary violation.
    Ensure your implementation satisfies all declared invariants:
    - {invariant_1}
    - {invariant_2}
    Check edge-case handling: duplicate values, empty inputs, boundary ranges, and explicit exception raising.
    ```
  - This directly solves `task_006` (duplicate preservation) and `task_015` (input validation) while maintaining zero data leakage.

### Objective 3: AST Semantic Pre-Flight (Gate 2 Extension)
- **Problem**: Models pass Gate 2 (AST) as long as function names exist, even when the contract explicitly demands exception handling (e.g., `Raise ValueError`) that the model completely omitted.
- **Solution**:
  - In `_run_cage_gates` / AST validation, if any declared invariant contains `Raise <Exception>` or `raise <Exception>`:
    - Inspect the AST for `ast.Raise` nodes.
    - If zero `ast.Raise` nodes exist in the candidate, trigger an immediate Gate 2 failure:
      `AST Contract Failed: Task invariant requires input validation raising ValueError, but no Raise statements were found in implementation.`
  - This eliminates wasteful test execution on unvalidated code and forces small models to implement boundary checks on Attempt 1.

### Objective 4: Automated Negative & Boundary Probing Gate
- **Problem**: Models write happy-path logic that collapses on edge cases (e.g., empty string `""`, empty list `[]`, negative numbers, duplicate elements).
- **Solution**:
  - Add an optional universal pre-check gate that fuzzes functions with canonical empty/zero inputs (`""`, `[]`, `0`) to catch unhandled `IndexError` or `ZeroDivisionError` before full suite evaluation.

---

## Part 3: Phased Implementation Instructions

### Phase 1: Diagnostic Granularity in `src/cdavc/benchmark.py`
1. Update `_run_cage_gates` to pass `include_output=True` for `targeted_test` and `regression`, but `include_output=False` for `hidden_test`.
2. In `_prompt()`, format targeted test failures with safe workspace-relative tracebacks, while formatting hidden test failures with the task's declared invariant checklist.

### Phase 2: AST Semantic Validation in `src/cdavc/benchmark.py` & `src/cdavc/supervisor.py`
1. Extend `_run_cage_gates` AST check to inspect function bodies for `ast.Raise` when `invariants` require raising exceptions.
2. Add unit tests in `tests/test_benchmark.py` and `tests/test_supervisor.py` verifying that:
   - Missing required exceptions are caught at Gate 2.
   - Public test tracebacks are visible on retry.
   - Hidden test outputs remain 100% redacted.

### Phase 3: Empirical Validation Across All 30 Tasks
1. Run `make test PYTHON=.venv/bin/python` to ensure zero regression in the 61-test suite.
2. Run `make benchmark-mock PYTHON=.venv/bin/python` to confirm deterministic CI/mock compliance.
3. Execute the full 30-task real-model benchmark with `Qwen2.5-7B-Instruct`:
   ```bash
   PYTHONPATH=src .venv/bin/python -m cdavc.benchmark . \
     --tasks benchmarks/tasks.json \
     --endpoint http://127.0.0.1:8080/v1/chat/completions \
     --model 'Qwen2.5-7B-Instruct' \
     --quantisation 'Q4_K_M' \
     --version 'bb5d59e0' \
     --hardware 'Darwin 27.0.0 arm64' \
     --seed 20261019 \
     --timeout 120 \
     --retry-cap 3
   ```
4. Verify that:
   - `cdavc` pass rate strictly exceeds `baseline_single` (target: ≥ 85%).
   - Paired difference confidence interval 95% CI is strictly positive.
   - Measured cage-hurt cases remain 0.
   - Prompt token consumption remains lower than `baseline_retry`.
5. Update `docs/benchmark_comparison.svg` with the full 30-task final empirical measurements.
