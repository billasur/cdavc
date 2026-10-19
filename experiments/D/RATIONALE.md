# Experiment D: arity-aware boundary probe (Objective 4 follow-up)

Status: prepared, not measured. No benchmark was run for this patch.

## Finding about the current code (quoted from src/cdavc/benchmark.py at 3e54f5d)
- Objective 4 is already implemented as `BOUNDARY_PROBE` and `_run_boundary_probe`, gated by `BenchmarkTask.boundary_probe` (default False).
- `benchmarks/tasks.json` has no `boundary_probe` key (grep count 0), so the 30-task cage arm in results/REPORT30.md ran with the probe off.
- The probe calls `function(argument)` with ONE argument for `""`, `[]`, `0` and only fails on IndexError or ZeroDivisionError. Any symbol that needs two or more arguments raises TypeError on that call, which is swallowed, so the probe does nothing for it.
- Tasks in tasks.json with multi-argument signatures by title/invariant include chunk a list (size), merge sorted lists, rotate, top-k, binary search, Levenshtein, matrix multiplication. I did not inspect each signature against a model output; this is from task titles only.

## Single change
Use `inspect.signature` to count required positional parameters and call `function(*[argument] * required)` (minimum 1, so the existing one-argument behaviour is unchanged). Nothing else changes: same inputs, same two exception types, still opt-in.

## Hypothesis
H: for multi-argument tasks, the opt-in probe becomes able to reject candidates that crash with IndexError/ZeroDivisionError on empty/zero inputs before the full suite runs, with no change for single-argument tasks. Falsified if, with boundary_probe enabled on all 30 tasks, cdavc pass rate and the set of rejected attempts are identical with and without this patch.
Caveat: the probe passes the same value for every argument, so it is a crude stress, and it can false-reject a valid solution that legitimately lets IndexError escape for such input. To measure that, run the 30 tasks with boundary_probe=true both before and after the patch and compare gate_results and cage-hurt cases.

## Verification done
- `PYTHONPATH=src python3 -m unittest tests.test_benchmark`: 16 tests pass (15 existing plus one new test for a two-argument function). Before the patch: 15 pass. This is a unit check, not a benchmark measurement.

## Sources
- inspect.signature and Parameter.kind / default: https://docs.python.org/3/library/inspect.html
- Objective 4 text: docs/MASTER_EXPERIMENT_PROMPT.md in this repo.
