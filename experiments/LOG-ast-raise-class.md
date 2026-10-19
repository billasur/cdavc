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
