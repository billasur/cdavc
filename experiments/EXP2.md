# Experiment 2: first-failure-only repair feedback (prepared, not measured)

Status: prepared, not measured. No benchmark was run for this change. Unit
tests only (see "Test state").

Change lives on branch `night-run-patch-exp-2` (branched from `night-run`):
- `src/cdavc/benchmark.py`: new `_first_failure_excerpt()` helper; `_cage_repair`
  now forwards the excerpted first failure instead of the full sanitised gate
  output (previously up to the last 4000 chars of combined stdout+stderr).
- `tests/test_exp2_first_failure.py`: 10 unit tests.

Branch-name note: `night-run/exp-2` cannot exist because the ref
`refs/heads/night-run` already exists (git cannot have both a ref and a
namespace with the same name), so the repo's `night-run-patch-*` convention
was used instead.

## What the change does (one change only)

When a public gate (targeted / negative / regression / boundary probe) fails,
the retry prompt for the `cdavc` arm used to get the whole sanitised output.
Now it gets only the first failing assertion region:

- unittest-style output: the first `FAIL:`/`ERROR:` block (header plus its
  traceback), later blocks dropped.
- other output: everything before the first failure-looking line
  (`Traceback ...`, `AssertionError`, ` failed`, `error:`) is dropped, so
  candidate stdout noise no longer enters the prompt.
- no recognisable failure: output is returned whole (behaviour unchanged).
- every path is bounded to 800 chars; an over-long region keeps its head and
  its tail (the assertion message sits at the end) with a `[...]` marker.

Nothing else changes: same arms, same attempt budget, same gates, same
recorded `attempt_log` failure text (records keep the full output; only the
prompt is excerpted). The hidden gate stays categorical - no hidden test
content is touched. The `baseline_retry` arm still gets the raw failure
string and serves as the unmodified control.

## Hypothesis

H: on retry, a model given only the first failing assertion (plus its
traceback) repairs the candidate at least as often as one given the full
gate output, using fewer prompt tokens. SWE-agent showed concise, structured
tool feedback beats raw output dumps for agents; long dumps dilute the
signal and can push small local models into addressing noise (stdout junk,
later cascading failures) instead of the first real failure.

Falsified if, at equal seeds and attempt budget, the patched arm's pass rate
is lower than control beyond sampling noise (Wilson intervals overlap is
inconclusive, not falsification) or the excerpt provably drops information a
repair needed (inspect `attempt_log` divergences task by task).

Expected-null caveat: the 30-task corpus gates already print single-line
failures (`public test failed for task_NNN: expected X, got Y`), so on that
corpus the excerpt is usually identical to the old behaviour and a null
result is consistent, not informative. The change discriminates on verbose
output: unittest-style suites (as in `tests/` and the held-out task
format), import/syntax tracebacks, and candidates that print to stdout. A
held-out suite with multi-test unittest output is the better measurement
target.

## How to measure on the Mac (one change, 3 seeds, Wilson CI)

Setup: Python 3.11 or 3.12 (pyproject pins `>=3.11,<3.13`), the same local
endpoint, model, quantisation and `--retry-cap` as `results/REPORT30.md`.
Do not compare against REPORT30 numbers: any run here is a new run.

For each seed s in three fixed seeds (e.g. 11, 22, 33 - same three for both
arms), same machine, same model server:

```sh
# control (unmodified night-run)
git checkout night-run
PYTHONPATH=src python3 -m cdavc.benchmark . \
  --tasks benchmarks/tasks.json \
  --endpoint http://localhost:8080 --model <model-name> \
  --seed <s> --records results/exp2_control_s<s>.jsonl \
  --report results/exp2_control_s<s>.md

# treatment (this patch)
git checkout night-run-patch-exp-2
PYTHONPATH=src python3 -m cdavc.benchmark . \
  --tasks benchmarks/tasks.json \
  --endpoint http://localhost:8080 --model <model-name> \
  --seed <s> --records results/exp2_patched_s<s>.jsonl \
  --report results/exp2_patched_s<s>.md
```

Compare only the `cdavc` arm records across the two files (baselines should
be identical and act as a sanity check). For each arm, per seed: passes k
out of n=30; report the Wilson 95% interval:

```python
import math
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, centre - margin, centre + margin
```

Also compare `token_in` on the `cdavc` arm (shorter feedback should not cost
more tokens) and diff `attempt_log` per task to find any repair that changed
because of the excerpt. Judge on all three seeds together, not one.

## Sources

- SWE-agent (concise, structured tool feedback): https://arxiv.org/abs/2405.15793
- Research note selecting this experiment: experiments/RESEARCH.md, section 4
  ("Suggested single-change experiments", item 2).
- Repo code: `src/cdavc/benchmark.py` (`_cage_repair`, `_run_command`,
  `_failure_category`, `_is_hidden_failure`, `HIDDEN_GATE_LABEL`).

## Test state

Sandbox has only Python 3.10.12; the project requires >=3.11,<3.13, so the
required-version run was NOT done. Indicative run under 3.10:
`PYTHONPATH=src python3 -m unittest discover -s tests` -> 77 tests, 1 error
(`test_launch.test_main_detects_memory_when_not_explicitly_configured`),
which fails identically on unmodified `night-run` (pre-existing, unrelated).
The 10 new tests pass. Re-run the suite under 3.11/3.12 on the Mac before
trusting it.
