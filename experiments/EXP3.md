# Experiment 3: retry with feedback vs fresh independent sample at equal attempts

Status: prepared, not measured. No benchmark run exists for this arm. Branch: night-run-exp-3
(requested name night-run/exp-3 is not a legal git ref while branch night-run exists, so a dash is used).

## Finding about the current code (night-run, before this patch)

Experiment 3 from experiments/RESEARCH.md ("Retry with feedback vs fresh independent sample at equal
attempts", Self-Repair control) was NOT implemented. src/cdavc/benchmark.py had exactly three arms
(`baseline_single`, `baseline_retry`, `cdavc`). `baseline_retry` retries up to
`min(task.max_retries, retry_cap) + 1` attempts and feeds the previous failure output back into the
next prompt (`_prompt`, repair block). No arm resampled without feedback, so the 80.0% vs 53.3%
retry-over-single gain in results/REPORT30.md cannot be attributed to the feedback itself: it
confounds feedback with simply drawing more samples (Large Language Monkeys effect).

## Single change

New benchmark arm `baseline_fresh` (src/cdavc/benchmark.py only, plus tests):

- Same attempt budget as `baseline_retry`: `min(task.max_retries, retry_cap) + 1` (the existing
  `max_attempts` line already covers any arm that is not `baseline_single`).
- Every attempt sends the identical first-attempt prompt: `_prompt` only adds repair text for
  `baseline_retry` and `cdavc`, so `baseline_fresh` never sees a failure trace.
- Independence comes from the seed, not the prompt: `_complete` uses `seed + attempt - 1` for
  `baseline_fresh` only. With a fixed seed and an unchanged prompt, a deterministic local server
  would replay attempt 1 verbatim and the control would measure nothing. All other arms keep the
  original seed for every attempt, so their behaviour is bit-identical to before.
- `_provider_for` falls back to the `baseline_retry` entry of a provider mapping when
  `baseline_fresh` is absent, so existing three-arm provider configs run unchanged. Both arms must
  sample the same model.
- Records flow through the existing JSONL/report path (ARMS-driven), so the report gains a fourth
  row with no further code.

## Hypothesis

H: on the 30-task benchmark, at equal attempt budget, `baseline_retry` (feedback) beats
`baseline_fresh` (no feedback) by less than the naive reading of REPORT30 suggests, i.e. a large
share of the retry gain is repeated sampling, not repair signal. This is the Self-Repair paper's
central control: repair gains are modest once the cost of extra samples is counted, and are
bottlenecked by feedback quality.

Falsified if the paired per-task difference (`baseline_retry` minus `baseline_fresh`) has a 95% CI
bounded clearly away from 0 in either direction across seeds. A CI containing ~0 supports the
hypothesis that feedback adds little beyond extra draws on this benchmark.

Caveat: `baseline_fresh` prompts differ from `baseline_retry` prompts by the arm label line
("Benchmark arm: baseline_fresh.") even on attempt 1. This is unavoidable without lying to the
model; it is constant across attempts and seeds.

## How to measure it on the M3 Air (one change, 3 seeds, Wilson CI)

1. `git checkout night-run-exp-3` in a clean clone. Keep the same model, quantisation, server
   build, hardware, `--retry-cap 3` and task set as results/REPORT30.md, or the run is not
   comparable to it. The llama.cpp server must honour the `seed` parameter (default server does).
2. Run the full benchmark once per seed, three seeds total, separate records/report paths:

   ```bash
   for SEED in 101 202 303; do
     PYTHONPATH=src .venv/bin/python -m cdavc.benchmark . \
       --tasks benchmarks/tasks.json \
       --records results/exp3-records-$SEED.jsonl \
       --report results/EXP3-REPORT-$SEED.md \
       --endpoint http://127.0.0.1:8080/v1/chat/completions \
       --model 'Qwen2.5-7B-Instruct' \
       --quantisation 'Q4_K_M' \
       --version 'bb5d59e0' \
       --hardware 'Darwin 27.0.0 arm64' \
       --seed $SEED \
       --timeout 120 \
       --retry-cap 3
   done
   ```

   (Seeds 101/202/303 are arbitrary; any three fixed values work if you record them.)
3. Per seed, read pass rates for `baseline_retry` and `baseline_fresh` from the generated report,
   then compute a Wilson 95% CI for each arm and the paired difference with the repo's own
   `paired_pass_rate_difference(records, "baseline_retry", "baseline_fresh")`. Stdlib Wilson
   snippet (n=30 per arm per seed):

   ```python
   import math
   def wilson(k, n, z=1.96):
       p = k / n
       d = 1 + z * z / n
       c = p + z * z / (2 * n)
       m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
       return ((c - m) / d, (c + m) / d)
   ```

4. Report the three per-seed paired differences with CIs. Only pool seeds if the per-seed results
   agree in sign. n=30 tasks x 3 seeds is still small; treat a CI spanning 0 as "no detected
   difference", not "no difference".

## Verification done (sandbox, not the Mac)

- `PYTHONPATH=src python3 -m unittest tests.test_benchmark`: 16 tests pass (15 existing, two of
  them updated for the fourth arm, plus one new test
  `test_baseline_fresh_resamples_independently_without_failure_feedback` that asserts equal attempt
  budget, byte-identical retry prompts, no failure text in fresh prompts, and per-attempt seeds
  [17, 18] for fresh vs [17, 17] for retry).
- Full suite: 68 tests, 67 pass; the one error
  (`test_launch.test_main_detects_memory_when_not_explicitly_configured`) also fails on unpatched
  night-run in this sandbox (it probes real machine memory) and is unrelated.
- Sandbox Python is 3.10.12, not 3.11/3.12. Re-run `make test` on the Mac before trusting it there.
- No benchmark arm was executed against a model. All numbers above are unit-test counts only.

## Sources

- https://arxiv.org/abs/2306.09896 (Is Self-Repair a Silver Bullet? On the Effectiveness of
  Iterative Self-Repair for Code Generation) - the control this arm implements.
- https://arxiv.org/abs/2304.05128 (Self-Debugging) - feedback-driven repair being controlled for.
- https://arxiv.org/abs/2407.21787 (Large Language Monkeys) - pass rate rises with sample count
  alone under a verifier; the confound this arm isolates.
