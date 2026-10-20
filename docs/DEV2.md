# dev2: harder CD-AVC dev set (13 tasks, drafted at zero Groq tokens)

Location: benchmarks_dev2/agent10/task_e01..e13. Build: `python3 scripts/dev2/build.py`. Verify: `python scripts/dev2/verify.py`.
Not held-out. Written without reading any held-out tests; domains chosen to avoid held-out directory names.
Verification (measured, offline): for all 13 tasks the reference passes public, hidden and regression tests; the stub and a trivial wrong solution both fail hidden tests. Wrong solution also fails public tests on all 13 (so public tests are not a weak signal here; hidden-only traps are in hidden_tests.py).
Mutation kill rate (cdavc.mutants, up to 20 mutants/task): 219/236 = 0.928 overall (see benchmarks_dev2/mutation_report.json).
Cross-checks: min_coins vs brute force, format_bytes vs Decimal rounding. osa_distance only re-checked against the same recurrence (sanity, not independent).
No model has been run on these tasks. Difficulty for gpt-oss-20b is a hypothesis, not a measurement.

## Lenient parser (opt-in, branch night-run-lenient)
`--lenient-parse` (env `LENIENT=1` in scripts/run_openrouter.sh) recovers a files object from prose/fences, trailing commas, bad escapes, a bare path->code object, one python block for a single-file task, and a missing final `}`. `--raw-failures PATH` saves unparseable raw responses. Default behaviour is unchanged. Unit tests (synthetic): tests/test_lenient_parse.py.
