## Experiment D - arity-aware boundary probe (prepared, not measured)
- Hypothesis: calling each symbol with all required args (not one) lets the existing opt-in boundary probe reject empty/zero-input crashes on multi-arg tasks. Falsified if pass rate and rejections are unchanged with boundary_probe enabled on all 30 tasks.
- Change: src/cdavc/benchmark.py BOUNDARY_PROBE only (see experiments/D/PATCH.diff; code on branch night-run/patch-D). Plus one unit test.
- Note: the probe is off by default and off in tasks.json, so REPORT30 did not exercise it; an arm run must enable boundary_probe for it to matter.
- Evidence: unit tests only (16 pass). Sources: https://docs.python.org/3/library/inspect.html
- Status: prepared, not measured.
