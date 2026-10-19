# ast-diag: name the AST gate failure (prepared, not measured)

Status: prepared, not measured. No benchmark was run for this change.

## Objective 1 check
MASTER_EXPERIMENT_PROMPT Part 2, Objective 1 (public gates return output, hidden gate stays categorical) is already implemented in src/cdavc/benchmark.py at main 3e54f5d:
- `_run_cage_gates` passes `include_output=True` for targeted_test, negative_test, regression and boundary probe.
- The hidden gate calls `_run_command` without it, so it raises only "<label> failed".
- `_run_command` rewrites workspace and root paths to `$WORKSPACE` / `$PROJECT_ROOT` and keeps the last 4000 chars.

## Remaining gap on the same theme
Gate 2 (AST contract) is also built from public information (the allowed files and required symbols are in the repair prompt already) but its failures carry no detail:
- `raise _GateFailure("AST contract failed")` on SyntaxError/OSError: no file, line or message.
- `raise _GateFailure("AST contract is missing a required symbol")`: does not say which symbol.
`src/cdavc/supervisor.py` (the v1 runner) already reports `relative:lineno: msg` and the missing symbol list, so the benchmark cage gives the model less than the product code does.

## Change (one)
In `_run_cage_gates`: SyntaxError -> `AST contract failed: <file>:<line>: <msg>`; OSError -> `AST contract failed: <file>: could not read file`; missing symbols -> `AST contract failed: missing required symbols [..]`. `_cage_repair` already forwards text after the first colon for non-hidden categories, so no other edit is needed.

## Hypothesis
A model that emits a syntax error or omits a required symbol repairs it more often on retry when told the line/name, as with a human engineer's compiler output. Expected effect: small, only on tasks whose failure is Gate 2. Not tested; the 20-task failures in the doc (task_006, 013, 015) are hidden-test or Raise-check cases, not Gate 2, so this may show no change on that set.

## Privacy
No hidden test content is touched: the new text comes from the candidate's own source and the public `task.symbols`.

## Sources
- Repo code: src/cdavc/benchmark.py (`_run_cage_gates`, `_run_command`, `_cage_repair`), src/cdavc/supervisor.py (`_verify`)
- docs/MASTER_EXPERIMENT_PROMPT.md Part 2, Objective 1
- No external URLs used; none needed for the claim above.

## Test state
`PYTHONPATH=src python3 -m unittest discover -s tests`: 67 tests, 1 error (test_launch.test_main_detects_memory_when_not_explicitly_configured), which fails identically without this patch (checked with git stash).
