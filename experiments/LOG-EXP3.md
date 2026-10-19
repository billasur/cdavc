## Experiment 3 - fresh independent sample control arm (prepared, not measured)
- Hypothesis: at equal attempts, retry-with-feedback beats fresh resampling by less than REPORT30's
  naive retry gain implies (Self-Repair control). Falsified if the paired baseline_retry minus
  baseline_fresh 95% CI is bounded away from 0 across 3 seeds.
- Change: new arm baseline_fresh in src/cdavc/benchmark.py (see experiments/EXP3/PATCH.diff; code on
  branch night-run-exp-3). Identical prompt every attempt; per-attempt seed for independence;
  provider mapping falls back to baseline_retry. Other arms unchanged.
- Evidence: unit tests only (16 pass, sandbox Python 3.10.12). Sources in experiments/EXP3.md:
  arxiv 2306.09896, 2304.05128, 2407.21787.
- Status: prepared, not measured.
