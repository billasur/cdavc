# LOG exp1 (20 Oct 2026, night-run)

- exp1 (latest vs cumulative retry feedback): status "prepared, not measured".
- Check: latest-only was already the behaviour in benchmark.py and supervisor.py; the cumulative arm did not exist.
- Change: `--feedback-mode` on BenchmarkRunner/CLI, baseline_retry arm only; cdavc arm unchanged (hidden-gate parse safety); mode recorded per record; resume-mix guard. PATCH.diff + RATIONALE.md in experiments/exp1/, full entry experiments/EXP1.md.
- Tests: 72 run, 5 new pass; 1 pre-existing test_launch error unchanged (verified via git stash). Ran under Python 3.10 (sandbox has no 3.11/3.12) - re-run on the Mac.
- Side observation (not this change): same-second same-size file writes can serve stale __pycache__ bytecode in the baseline temporary-copy workspace with instant mock providers.
