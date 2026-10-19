# night-run layout (overnight improvement effort, 20 Oct 2026)

Branch: night-run only. Never push to main. Commit identity: billasur / singhgaurprahalad@gmail.com.
Push with a rebase first (`git pull --rebase origin night-run`); each agent writes only its own paths.

Paths
- Held-out writers: `benchmarks_heldout/agentN/task_hNN_xxx/` (N=1..6, 5 tasks each).
  Each task dir: `spec.json` (same fields as one entry in benchmarks/tasks.json: task_id, title, description, implementation_files, symbols, invariants, max_retries),
  `solution_stub.py` (incomplete start file), `reference_solution.py` (passes everything), `public_tests.py`, `hidden_tests.py`, `regression_tests.py`.
  Tests are stdlib-only, deterministic, exit non-zero on failure. Reference must pass all three. Stub must fail hidden.
  Do not copy HumanEval/MBPP tasks. Hidden tests must probe edge cases the spec states in its invariants.
- Patch analysts: `experiments/<id>/` with `PATCH.diff` (one change only), `RATIONALE.md`, and a `LOG.md` entry appended as `experiments/LOG-<id>.md` (merged into LOG.md by the lead). Source URLs for any research claim. Label anything unmeasured as "prepared, not measured".
- Researcher: `experiments/RESEARCH.md` with URLs.
- Lead: freeze manifest `benchmarks_heldout/MANIFEST.sha256`, LOG.md, REPORT.md.
Rules: one change per experiment, same sample budget and stdlib line for all arms, no hidden test content in any model prompt, no fabricated numbers.
