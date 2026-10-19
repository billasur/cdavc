# LOG (night-run, 20 Oct 2026)

Merged from per-experiment entries. Every entry is prepared, not measured unless it says otherwise.

---
<!-- experiments/LOG-D.md -->
## Experiment D - arity-aware boundary probe (prepared, not measured)
- Hypothesis: calling each symbol with all required args (not one) lets the existing opt-in boundary probe reject empty/zero-input crashes on multi-arg tasks. Falsified if pass rate and rejections are unchanged with boundary_probe enabled on all 30 tasks.
- Change: src/cdavc/benchmark.py BOUNDARY_PROBE only (see experiments/D/PATCH.diff; code on branch night-run/patch-D). Plus one unit test.
- Note: the probe is off by default and off in tasks.json, so REPORT30 did not exercise it; an arm run must enable boundary_probe for it to matter.
- Evidence: unit tests only (16 pass). Sources: https://docs.python.org/3/library/inspect.html
- Status: prepared, not measured.

---
<!-- experiments/LOG-ast-diag.md -->
## ast-diag (failure analyst, cluster A) - prepared, not measured
- Hypothesis: naming the file/line/symbol in AST-gate failures improves repair on retry for Gate 2 failures. Single change, src/cdavc/benchmark.py, 3 lines.
- Objective 1 (public output vs hidden categorical) already implemented in benchmark.py; this is the next gap on that theme.
- Code branch: night-run-patch-ast-diag (the name night-run/patch-X is impossible in git because the ref night-run exists). Diff: experiments/ast-diag/PATCH.diff
- Sources: repo code and docs/MASTER_EXPERIMENT_PROMPT.md only. No measured result.

---
<!-- experiments/LOG-ast-raise-class.md -->
# LOG entry: ast-raise-class (20 Oct 2026, night-run)

- **Agent role:** failure analyst (Objective 3 follow-up).
- **Status:** prepared, not measured.
- **Finding:** Objective 3 (AST raise pre-flight) is already implemented
  (`src/cdavc/benchmark.py` `_run_cage_gates`, `src/cdavc/supervisor.py`
  `_verify`, `src/cdavc/invariants.py`), so this entry proposes the next
  single change on the same theme.
- **Hypothesis:** when an invariant declares `Raise <Exception>`, requiring an
  AST-level raise of that named class (plain/call/attribute form) rejects
  contract-violating candidates at Gate 2 - candidates that today pass with
  any unrelated `raise` and burn test-gate attempts. Unmeasured.
- **Change:** `raises_exception(tree, name)` replaces
  `has_raise_statement(tree)` in `src/cdavc/invariants.py` and both call
  sites; see `experiments/ast-raise-class/PATCH.diff` and `RATIONALE.md`;
  code on branch `night-run/patch-ast-raise-class`.
- **Local validation:** unit suite 78 tests, only pre-existing sandbox error
  (`test_launch` memory detection, also fails on base); mock benchmark 30/30
  all arms, deterministic. No real-model measurement taken.
- **Source URLs:** https://docs.python.org/3/library/ast.html ;
  supporting theme evidence: `docs/MASTER_EXPERIMENT_PROMPT.md` (`task_015`).

---
<!-- experiments/LOG-hidden-guidance-escalation.md -->
# LOG - hidden-guidance-escalation

- Date: 2026-10-20 (night-run)
- Analyst: failure analyst (Objective 2 theme). Objective 2 itself is already
  implemented on night-run; this entry is the next single change on that theme.
- Change: escalate invariant-anchored guidance on the second consecutive
  hidden-gate rejection (strategy-shift block appended; gates untouched).
  Patch: experiments/hidden-guidance-escalation/PATCH.diff; code branch:
  night-run-patch-hidden-guidance-escalation.
- Hypothesis: identical repeated guidance on attempts 2-3 lets a small local
  model keep minimally editing a failing candidate; an explicit
  rebuild-and-trace directive on the repeat adds leak-free signal and
  unblocks some of those stalls. Grounded in the session note's observation
  that task_013/task_029 miss the hidden gate at attempts 2-3 despite correct
  public diagnostics, and in results/REPORT30.md (cdavc 23/30).
- Status: prepared, not measured. Local checks only: 68-test unit suite OK on
  the branch (one pre-existing, environment-only test_launch error, identical
  on unmodified night-run; sandbox runs Python 3.10 vs the repo's 3.11 target)
  and mock benchmark 30/30 all arms with 0 cage-hurt. No real-model numbers
  exist for this change; the 30-task Qwen2.5-7B run is still to be executed
  on the M3 Air.
- Sources:
  - https://github.com/billasur/cdavc/blob/night-run/src/cdavc/benchmark.py
  - https://github.com/billasur/cdavc/blob/night-run/results/REPORT30.md
  - https://github.com/billasur/cdavc/blob/night-run/docs/MASTER_EXPERIMENT_PROMPT.md
  - https://github.com/billasur/cdavc/blob/night-run/.ogcode/memory/2026-10-19T193723Z--ses01M5ARMDHDNA--cd-avc-verification-cage-upgrade-30-task-benchmark.md
  - https://arxiv.org/abs/2310.01798
  - https://arxiv.org/abs/2303.11366

---
## Research
See experiments/RESEARCH.md (source URLs inside).

## exp-1, exp-2, exp-3 (no LOG file was written by their helpers; from commit messages)
- night-run-patch-exp-1: latest vs cumulative retry feedback mode (prepared, not measured). Related source: https://dl.acm.org/doi/pdf/10.1145/3843282.3844438
- night-run-patch-exp-2: first-failure-only cage repair feedback (prepared, not measured)
- night-run-exp-3: baseline_fresh arm, a fresh-sample control with equal attempts and per-attempt seed (prepared, not measured)
