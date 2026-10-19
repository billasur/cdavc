## ast-diag (failure analyst, cluster A) - prepared, not measured
- Hypothesis: naming the file/line/symbol in AST-gate failures improves repair on retry for Gate 2 failures. Single change, src/cdavc/benchmark.py, 3 lines.
- Objective 1 (public output vs hidden categorical) already implemented in benchmark.py; this is the next gap on that theme.
- Code branch: night-run-patch-ast-diag (the name night-run/patch-X is impossible in git because the ref night-run exists). Diff: experiments/ast-diag/PATCH.diff
- Sources: repo code and docs/MASTER_EXPERIMENT_PROMPT.md only. No measured result.
