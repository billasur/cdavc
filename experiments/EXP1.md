# EXP1: latest-trace-only vs cumulative retry feedback (prepared, not measured)

Status: prepared, not measured. No benchmark run exists for this change. Unit tests were run under Python 3.10 (the sandbox has no 3.11/3.12; the repo declares 3.11+), so they must be re-run on the Mac before any measurement.

## Already-implemented check

Experiment 1 from `experiments/RESEARCH.md` ("latest-trace-only retry feedback vs cumulative feedback") is half implemented already:

- `src/cdavc/benchmark.py` `_run_arm` kept a single `failure` string, overwritten on every failed attempt, so retry prompts already received only the LATEST trace.
- `src/cdavc/supervisor.py` (v1 runner) does the same with `previous_failure`.

What did not exist: the cumulative arm (arm A of the experiment). There was no way to measure the comparison.

## The one change

Add a `feedback_mode` option to `BenchmarkRunner` / `python -m cdavc.benchmark`:

- `latest` (default, exactly the status quo): the `baseline_retry` repair prompt carries only the most recent failure trace.
- `cumulative`: the `baseline_retry` repair prompt carries every prior failure trace of the current task run, labelled `Attempt N failure:`.
- The `cdavc` arm is deliberately unchanged: it always repairs from the latest sanitised failure. Its hidden-gate categorisation (`_failure_category` / `_is_hidden_failure`) parses the first line of one failure; feeding it joined traces would break that parse and could leak hidden-test content into prompts. Extending the experiment to the cage arm is a separate change.
- `feedback_mode` is written into every JSONL record and added to the resume-metadata guard, so a records file cannot silently mix modes.
- Nothing else changes: same arms, same `attempts = min(task.max_retries, retry_cap) + 1` budget in both modes, same gates, same seed handling.

Patch: `experiments/exp1/PATCH.diff` (src/cdavc/benchmark.py + tests/test_benchmark.py).

## Hypothesis

From "Looping Is Not Reliability" (source 1): stale failure traces from earlier candidates mislead repair; on 14B HumanEval-style tasks, feeding stale traces harmed 34/135 previously-correct starts vs 4/135 with current-candidate traces. So for CD-AVC's `baseline_retry` arm:

- H1: cumulative feedback passes fewer tasks than latest-only at equal attempt budget, because attempt-1 traces are stale by attempt 3.
- H0: no measurable difference on a small local model (the paper's numbers are 14B; the effect may shrink at 2B-9B, and the paper's own policy trial failed its joint criterion).

Either result is informative: if H0 holds on the Mac's model, latest-only stays (it is also the cheaper prompt).

## Sources

- https://dl.acm.org/doi/pdf/10.1145/3843282.3844438 ("Looping Is Not Reliability", typed revision contracts) - the experiment's basis; numbers above are from its abstract/excerpts as noted in `experiments/RESEARCH.md` (section 1, first source). Not re-verified for this entry.
- `experiments/RESEARCH.md` experiment 1 (night-run, 20 Oct 2026).
- Repo: `src/cdavc/benchmark.py` (`_run_arm`, `_prompt`, `_cage_repair`), `src/cdavc/supervisor.py` (`_run_task`, `_prompt`).

## How to measure on the Mac (one change, 3 seeds, Wilson CI)

Setup: checkout this branch, Python 3.11+, the local model serving an OpenAI-compatible endpoint (same model and quantisation for every run).

0. Re-run the unit tests first (sandbox ran them under 3.10 only):
   `PYTHONPATH=src python3 -m unittest discover -s tests`
   Expected: 72 tests, 1 pre-existing error in `test_launch.test_main_detects_memory_when_not_explicitly_configured` (fails identically without this patch, verified with git stash).

1. For each seed S in {0, 1, 2} and each mode M in {latest, cumulative}, run the same 30-task corpus with the same retry cap (6 runs total):
   ```
   PYTHONPATH=src python3 -m cdavc.benchmark . \
     --tasks benchmarks/tasks.json \
     --endpoint http://localhost:8080 --model <model> --quantisation <q> --version benchmark-v1 \
     --hardware "$(uname -srm)" \
     --seed S --feedback-mode M \
     --records results/exp1-M-sS.jsonl \
     --report results/exp1-M-sS.md
   ```
   Only `--feedback-mode` and the output paths change between arms of the experiment; nothing else.

2. Compare the `baseline_retry` records only. For each mode, pool the 3 seeds (90 task runs) and compute the pass rate with a Wilson score 95% CI:
   ```python
   import json, math
   def wilson(path, arm="baseline_retry"):
       rows = [json.loads(l) for l in open(path)]
       rows = [r for r in rows if r["arm"] == arm]
       n = len(rows); k = sum(1 for r in rows if r["pass"]); z = 1.96
       p = k / n; d = 1 + z * z / n
       centre = (p + z * z / (2 * n)) / d
       half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
       return k, n, (centre - half, centre + half)
   # run over results/exp1-latest-s{0,1,2}.jsonl merged and results/exp1-cumulative-s{0,1,2}.jsonl merged
   ```
   Also report the per-seed pass-rate difference (cumulative minus latest) on the 30 shared tasks, so a single noisy seed cannot carry the conclusion.

3. Decision rule: if cumulative's Wilson CI sits clearly below latest's, cumulative is harmful - keep latest (status quo) and close the experiment. If the intervals overlap heavily, H0 holds on this model - keep latest (simpler, shorter prompts) and note the null result. If cumulative is clearly better, re-read the paper caveat before changing the default, because that contradicts its central claim.

## Observed side note (not part of this change)

While testing with instant mock providers, two attempts inside the same second with same-size file writes can reuse a stale `__pycache__` bytecode file in the temporary-copy workspace, making attempt N+1's test run against attempt N's code. Real model latencies make this unlikely, but a fast cached provider could hit it. Logged here only; fixing it is a different change.
