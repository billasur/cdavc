# Self-improving CD-AVC via a pi extension

Status: PROTOTYPE built and offline-tested. No live (token-spending) run has
been executed. Nothing here is a measured improvement yet.

## Idea

The CD-AVC harness improves itself: propose a change, evaluate it on a fixed
benchmark, keep it only if it measurably helps, otherwise roll back. The
evaluator stays outside the improving agent's write access - the agent can
change how it is graded *next time* only within a bounded knob surface, never
the grading itself.

## Pieces

- `self_improve/config.py` - the editable surface: `retry_cap` (0..3),
  `prompt_layout` (default|stable-prefix), `lenient_parse` (bool). Each maps
  to an existing BenchmarkRunner argument. Validation rejects unknown keys,
  so the surface cannot widen itself.
- `self_improve/protected/tasks.json` - the fixed evaluation authority: the
  13 dev2 tasks, cdavc arm. Human-only changes.
- `self_improve/proposer.py` - ScriptedProposer (deterministic one-knob
  walk, offline) and a ModelProposer stub that refuses to run without an
  explicit spend approval.
- `self_improve/evaluator.py` - SimulatedEvaluator (hash-stub, mechanics
  tests only, results are NOT measurements) and LiveEvaluator (runs the real
  BenchmarkRunner, MEASURED, requires a token cap).
- `self_improve/controller.py` - the loop. Before every iteration it checks
  `self_improve/protected`, `benchmarks_dev2` and `benchmarks_heldout` are
  clean against git HEAD and aborts otherwise. Keep-if-better on measured
  pass count, tie-break on fewer tokens. Every step logged in
  `self_improve/IMPROVE_LOG.md`; keeps are committed, rejects rolled back.
- `pi_extension/cdavc/index.ts` - the pi coding-agent extension
  (https://github.com/badlogic/pi-mono, packages/coding-agent):
  - `cdavc_verify` tool: public gates + feedback for a dev2 task; hidden
    tests are never exposed.
  - write/edit guard over the protected evaluator paths.
  - `/cdavc-improve` command: simulated loop only. Live runs are CLI-only
    and require `--approve-spend --token-cap N`.

## Verified offline (measured: loop mechanics; not model results)

- 16 new tests in tests/test_self_improve.py, all pass, including a full
  BenchmarkRunner run of one real dev2 task through the cdavc arm (AST gate,
  public, hidden and regression tests in a git worktree) driven by a mock
  provider. Full suite: 111 passed, 1 pre-existing environmental failure
  (test_launch memory detection), unchanged by this work.
- Simulated CLI run: proposes, evaluates, rolls back, logs; config restored.

## Not done / open gaps (need user or lead decisions)

- Live measured run of the loop: needs a model key and a token cap approval.
  Groq gpt-oss-20b free tier was at its daily TPD cap as of 24 Oct ~16:00.
- Allowed self-edit surface is currently three config knobs. Widening it
  (e.g. feedback templates, parser code) is a human decision: each new
  surface needs its own guard so test/grading code stays out of reach.
- Objective is dev2 pass count, cdavc arm, seed 1. Single-seed comparisons at
  t=0.7 were previously shown to be as noisy as arm differences; a real
  improvement claim needs seeds and budget approval.
- The extension .ts is written against the documented pi extension API but
  has not been loaded in a live pi install (no pi in this sandbox).
- ModelProposer is a stub: proposing changes with a model spends tokens and
  needs approval first.
