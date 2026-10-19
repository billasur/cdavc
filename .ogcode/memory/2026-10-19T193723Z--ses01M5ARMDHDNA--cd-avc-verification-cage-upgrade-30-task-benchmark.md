---
title: "CD-AVC Verification Cage Upgrade & 30-Task Benchmark"
session_id: "ses_01M5ARMDHDNAV2HVGDJQZRJB2W"
session_type: "build"
project_id: "/Users/billasur/Projects/cdavc"
created_at: 2026-10-19T19:37:23Z
---

# CD-AVC Verification Cage Upgrade & 30-Task Benchmark

Topics: verification cage, AST raise gate, hidden-test leakage, boundary probe, Qwen2.5-7B benchmark, benchmark SVG

## Request

The developer supplied a "Master Engineering Prompt" (a copy of which was already saved at `docs/MASTER_EXPERIMENT_PROMPT.md`) to upgrade the CD-AVC verification cage in `/Users/billasur/Projects/cdavc` (Python 3.11+, stdlib-only, `.venv/bin/python`), based on a 20-task benchmark of `Qwen2.5-7B-Instruct` Q4_K_M on Apple Silicon.

### Baseline numbers given in the prompt
- `baseline_single`: 60.0% (12/20), 10.25s, 167.0 input tok.
- `baseline_retry`: 90.0% (18/20), 16.17s, 239.2 tok.
- `cdavc`: 85.0% (17/20), 16.44s, 230.5 tok.
- Paired gain +25.0 pts over single-shot, 95% CI `[0.055, 0.445]`; cage overhead vs plain retry +0.272s (+1.7%); 3.6% fewer input tokens than retry; cage-hurt rate 0.0%.

### Vulnerabilities described
1. **Test-leakage fallacy** — `baseline_retry` reaches 90% only because the harness dumps hidden/held-out test assertions into the repair prompt (e.g. `task_006`: `expected [-3, -2, 0, 0, 4, 9], got [-3, -2, 0, 4, 9]`).
2. **Zero regression & integrity protection** — retry never runs repo-wide regression tests, never checks AST symbols, cannot detect test tampering.

### Three CD-AVC failure cases analysed
- **`task_006`** (Merge Sorted Lists – Duplicates): model deduplicated `[-3, -2, 0, 4, 9]` instead of `[-3, -2, 0, 0, 4, 9]`; public test had no duplicates so it passed.
- **`task_013`** (Camel to Snake – Acronym Runs): failed `"HTTPRequest"` → `"http_request"`; retry passed only because fed the literal `"http_request"`; cdavc suppressed public/targeted test failure output during retries.
- **`task_015`** (Roman to Integer – Canonical Validation): invariant required `Raise ValueError for empty, non-canonical or out-of-range numerals` (e.g. `"IIII"`); model wrote a naive lookup adder.

### Four upgrade objectives
1. **Differentiate public diagnostics from hidden test privacy.** For Targeted/Public Tests (Gate 3) and Regression Tests (Gate 4) — public repository assets — capture stdout/stderr and format a clean diagnostic traceback without leaking workspace absolute paths. For Held-Out/Hidden Tests, preserve strict zero-leakage privacy; never expose hidden assertions, secret strings or expected outputs.
2. **Invariant-anchored semantic guidance on hidden failure.** When Gate 3 (Hidden) fails, extract the contract's declared `invariants` and synthesize:
   ```text
   Verification Gate Failed: Invariant check or edge-case boundary violation.
   Ensure your implementation satisfies all declared invariants:
   - {invariant_1}
   - {invariant_2}
   Check edge-case handling: duplicate values, empty inputs, boundary ranges, and explicit exception raising.
   ```
3. **AST semantic pre-flight (Gate 2 extension).** If any declared invariant contains `Raise <Exception>`/`raise <Exception>`, require ≥1 `ast.Raise` node; if zero exist, fail Gate 2 with `AST Contract Failed: Task invariant requires input validation raising ValueError, but no Raise statements were found in implementation.`
4. **Automated negative & boundary probing gate.** Optional universal pre-check that fuzzes functions with `""`, `[]`, `0` to catch unhandled `IndexError`/`ZeroDivisionError` before full suite evaluation.

### Phased instructions
- Phase 1: `_run_cage_gates` passes `include_output=True` for `targeted_test` and `regression`, `include_output=False` for `hidden_test`; `_prompt()` formats targeted failures with safe workspace-relative tracebacks and hidden failures with the invariant checklist.
- Phase 2: AST raise validation in `src/cdavc/benchmark.py` and `src/cdavc/supervisor.py`; unit tests in `tests/test_benchmark.py` and `tests/test_supervisor.py` covering missing-exception caught at Gate 2, public tracebacks visible on retry, hidden outputs 100% redacted.
- Phase 3: `make test PYTHON=.venv/bin/python` (61-test suite, zero regression), `make benchmark-mock PYTHON=.venv/bin/python`, then the full 30-task real run:
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
  Verify cdavc ≥ 85%, 95% CI strictly positive, cage-hurt 0, tokens lower than `baseline_retry`; update `docs/benchmark_comparison.svg`.

## What was done

### Code changes (completed, tested)
- **New `src/cdavc/invariants.py`** — `_RAISE_INVARIANT = re.compile(r"\braise\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))", re.IGNORECASE)`; `required_exception(invariants) -> str | None` (first invariant naming an exception class; prose like "raise an error" deliberately does not match); `has_raise_statement(tree) -> bool` (any `ast.Raise` via `ast.walk`).
- **`src/cdavc/benchmark.py`** — imports the two helpers; new constant `HIDDEN_GATE_LABEL = "hidden test"` and `BOUNDARY_PROBE` (stdlib `-c` script taking JSON `argv[1]` = `{"files": [...], "symbols": [...]}`, loading each file via `importlib.util.spec_from_file_location`, calling each callable symbol with `("", [], 0)`, printing `f"{symbol}({argument!r}) raised {type(exc).__name__}: {exc}"` to stderr and `raise SystemExit(1)` on `IndexError`/`ZeroDivisionError`; other exceptions ignored). `BenchmarkTask` gained `boundary_probe: bool = False` validated in `__post_init__` (`BenchmarkError("boundary_probe must be a boolean")`) and wired through `from_dict`/`from_task`. Repair-prompt assembly moved into `_cage_repair` / `_is_hidden_failure`; `_invariant_guidance` emits the checklist. `_run_cage_gates` gained the Gate-2 raise check after the missing-symbol check and the opt-in boundary probe.
- **`src/cdavc/supervisor.py`** — `_verify` calls the same helpers and raises `VerificationFailure(f"AST gate failed: Task invariant requires input validation raising {required}, but no Raise statements were found in implementation.")`.
- **Tests** — added 6 tests (4 in `tests/test_benchmark.py`, 2 in `tests/test_supervisor.py`): public traceback forwarded with `$WORKSPACE` sanitising and no absolute path leak; hidden failure shows invariants but never the assertion/secret; missing required exception rejected at Gate 2 before any test runs; boundary probe opt-in; supervisor rejects a candidate with no raise and accepts one that raises.

### Verification
- `make test PYTHON=.venv/bin/python` → **67 tests, OK** (up from 61). A trailing `/usr/bin/true -m …model.gguf…` line in the Makefile output is pre-existing noise.
- `make benchmark-mock PYTHON=.venv/bin/python` → all 3 arms 100% (30/30), deterministic.
- Full 30-task real run executed in the background (PID 91117) against the live server at `http://127.0.0.1:8080`, writing `results/benchmark30.jsonl` and `results/REPORT30.md`.

### Artifacts
- `docs/benchmark_comparison.svg` updated to 30-task numbers (+23.3% / CI [+7.9%, +38.7%], +2.70s vs retry, −2.5% tokens, bars rescaled, footnote → `results/benchmark30.jsonl`), validated with `xml.dom.minidom` and rendered via `qlmanage` then visually inspected.
- Prior runs preserved: `results/benchmark-20-task.jsonl` + `REPORT-20-task.md`, `results/benchmark-mock.jsonl` + `REPORT-mock.md`.
- `/Users/billasur/Projects/MEMORY.md` gained a "cdavc verification cage" section (helpers, gate output policy, `boundary_probe`, run command, 30-task numbers, leak forensics).

## Key files & symbols

- `src/cdavc/invariants.py` (new): `required_exception`, `has_raise_statement`, `_RAISE_INVARIANT`.
- `src/cdavc/benchmark.py`: `HIDDEN_GATE_LABEL`, `BOUNDARY_PROBE`, `BenchmarkTask.boundary_probe`, `_run_command`, `_run_cage_gates`, `_prompt`, `_cage_repair`, `_is_hidden_failure`, `_invariant_guidance`, `BenchmarkError`.
- `src/cdavc/supervisor.py`: `_verify`, `VerificationFailure`.
- `tests/test_benchmark.py`, `tests/test_supervisor.py`.
- `benchmarks/tasks.json` (30 tasks; 10 declare `raise ValueError`), `benchmarks/public_tests.py`, `benchmarks/hidden_tests.py`, `benchmarks/task_runner.py`, `benchmarks/regression_tests.py`, `benchmarks/mock_solutions/`.
- `docs/benchmark_comparison.svg`, `docs/MASTER_EXPERIMENT_PROMPT.md`, `results/`, `Makefile`, `.venv/bin/python`.

## 30-task measurements (Qwen2.5-7B-Instruct Q4_K_M, seed 20261019)

| Arm | Pass | Attempts | Wall | tok in |
|---|---:|---:|---:|---:|
| `baseline_single` | 16/30 (53.3%) | 1.00 | 13.76s | 166.8 |
| `baseline_retry` | 24/30 (80.0%) | 1.60 | 21.56s | 287.6 |
| `cdavc` | 23/30 (76.7%) | 1.53 | 24.26s | 280.4 |

- cdavc − single = **+23.3 pts, 95% CI [0.079, 0.387]** (strictly positive).
- Cage overhead **+2.70s (+12.5%) vs retry**; **2.5% fewer input tokens** than retry; **0 cage-hurt cases** (every cage failure also fails single-shot).
- One unique cage win: `task_024`.

## Decisions & why

- **Invariant guidance on hidden failure rather than richer failure text.** Assertion values are exactly what retry leaks; the contract's own invariant lines are the only leak-free edge-case signal. Consequence: `task_015` (explicit `Raise ValueError`) still fails — guidance informs but cannot substitute for model capability.
- **AST raise check as a Gate-2 rejection, not a warning.** Costs no test execution and forces validation on attempt 1 for the 10 tasks declaring it; kept in sync in `supervisor._verify` so both entry points behave identically.
- **Boundary probe left opt-in and unused by the 30 tasks.** A universal gate calling every callable with `0` would fail correct functions with non-zero domains; the false-rejection risk outweighs recall, and cage-hurt must stay 0.
- **Did not enrich `benchmarks/tasks.json` invariants to chase ≥85%.** Editing task data after seeing failures would tune the benchmark to its own answers — the overfitting the cage exists to prevent. Reversible if the developer wants a second run on re-specified task data.
- **Overhead card reports cage−retry (+2.70s)** because the card is titled "vs Retry"; the report's own `+10.51s` is vs single-shot.

## The ≥85% target: measured, not met

cdavc landed at 76.7%, not 85%. The gap is not a cage regression — it is where retry's three extra wins come from:

- **`task_013` / `task_029`**: retry passes only because the hidden expectation is printed in its prompt (`expected 'camel_case_value'`, `expected '0s', got ''`). The cage now forwards the *public* failure text for these (it did, on attempt 1), yet the model still misses the hidden gate at attempts 2–3.
- **`task_023` / `task_026`**: candidate imports `numpy` (`No module named 'numpy'`); the cage forwards that exact text and the model still does not remove it.
- **`task_030`**: provider returns non-JSON in all three arms.
- **`task_006` / `task_013` invariants under-describe their hidden tests** — 006's says only "may contain equal or negative values" while the hidden test requires duplicate preservation; 013's says nothing about acronym runs. That is task-data work, not cage work.

All Phase-3 criteria other than the raw pass-rate target pass.

## Commit state

The agent made **no commits**. Two commits appeared in the working repo from outside the session — `c97d59f "initial commit"` swept the `src/`/`tests/` changes (plus `.ogcode/` DB files and showcase work) into HEAD, and `f0a06cf "fix(docker)…"`. So the code edits are already committed while `docs/benchmark_comparison.svg` and `results/REPORT30.md` remain uncommitted. Unrelated dirty files (`.gitignore`, `showcase/*`, `.ogcode/`, `.freebuff/`) were deliberately left untouched.

## Outcome

- Phase 1 and Phase 2 implementation: **done and verified** — 67/67 tests pass, mock benchmark deterministic at 100% across all three arms.
- Phase 3 real-model benchmark: **executed and reported** — 30-task run completed, `results/benchmark30.jsonl` + `results/REPORT30.md` written.
- Pass-rate criterion (≥85%): **not met** (76.7%), with forensics recorded above; CI positivity, cage-hurt 0, and lower token consumption all met.
- `docs/benchmark_comparison.svg` updated and visually checked; older 20-task and mock artifacts preserved under renamed files.
- MEMORY.md updated. Nothing committed by the agent.
