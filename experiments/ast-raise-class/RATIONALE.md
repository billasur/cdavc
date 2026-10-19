# Experiment: ast-raise-class (AST gate requires the declared exception class)

Status: **prepared, not measured.**

## Objective 3 status check (as assigned)

Objective 3 of `docs/MASTER_EXPERIMENT_PROMPT.md` Part 2 (AST semantic
pre-flight: fail Gate 2 when an invariant declares `Raise <Exception>` but the
candidate contains no `raise`) is **already implemented** on `night-run`:

- `src/cdavc/benchmark.py`, `_run_cage_gates`:
  `required = required_exception(task.invariants)` then
  `if required and not has_raise_statement(tree): raise _GateFailure("AST Contract Failed: ...")`.
- `src/cdavc/supervisor.py`, `_verify`: same check, same helpers.
- `src/cdavc/invariants.py`: `required_exception()` parses the invariant,
  `has_raise_statement()` detects any `ast.Raise`.
- Covered by `tests/test_benchmark.py::test_cage_rejects_missing_required_exception_before_running_public_tests`
  and `tests/test_supervisor.py::test_supervisor_rejects_candidate_that_never_raises_required_exception`.

So this experiment proposes the next single change on the same theme that the
current code still lacks.

## Gap

The gate accepts **any** `raise` statement anywhere in the module. A candidate
that raises a different class than the contract declares - `raise TypeError`
when the invariant says `Raise ValueError`, or a bare `raise` re-raising an
unrelated error - passes Gate 2 and is only rejected later at the targeted or
hidden test gates. That costs a full test run per attempt and produces a
repair prompt that never tells the model which exception the contract
requires. (No measured instance of this exact failure exists in the repo: the
per-task records of the 30-task run are not committed, and the 20-task
analysis in `docs/MASTER_EXPERIMENT_PROMPT.md` documents a *missing* raise on
`task_015`, which the current gate already catches. The wrong-class case is
the documented check's uncovered sibling, stated here as a hypothesis.)

## Hypothesis

When a task invariant declares `Raise <Exception>`, requiring the AST to
contain a raise of that named class (plain, call, or attribute form) will
reject non-complying candidates at Gate 2 with an explicit message naming the
required class, instead of letting them consume test-gate attempts. Expected
effect: fewer wasted attempts on contract-violating candidates and clearer
repair signals; no effect on candidates that already raise the declared
class. Prepared, not measured.

## Change (one change)

`src/cdavc/invariants.py`: replace `has_raise_statement(tree)` with
`raises_exception(tree, name)`, which returns true only when an `ast.Raise`
node's exception expression resolves by name to the declared class
(`raise ValueError`, `raise ValueError(...)`, `raise errors.ValueError(...)`).
Call sites in `src/cdavc/benchmark.py` and `src/cdavc/supervisor.py` pass the
declared class through; the failure message now says
`"...but no raise of {required} was found in implementation."`
Tests: new `tests/test_invariants.py` (9 unit tests), plus wrong-class
rejection tests in `tests/test_supervisor.py` and `tests/test_benchmark.py`;
the one existing message assertion is updated.

## Local validation (mechanics, not model measurement)

- `python3 -m unittest discover -s tests`: 78 tests, same single pre-existing
  error on pristine base (`test_launch.LaunchTests.test_main_detects_memory_when_not_explicitly_configured`,
  environment memory detection in this sandbox); no new failures.
- `python3 -m cdavc.benchmark . --tasks benchmarks/tasks.json --mock --seed 0`:
  deterministic mock run, 30/30 pass in all arms, matching `results/REPORT-mock.md`.
- No real-model benchmark was run; the hypothesis above is unmeasured.

## Known limits

- Name match only: a locally defined subclass of the required exception is not
  resolved statically and is rejected (the message names the required class).
- A bare `raise` re-raise never counts, since its class is not statically
  determinable.
- The check still scans the whole module; a raise inside an unused helper
  satisfies it. Tightening scope to the declared symbols would be a separate
  change.

## Sources

- Python `ast` module documentation (structure of `ast.Raise`, `ast.Call`,
  `ast.Name`, `ast.Attribute`): https://docs.python.org/3/library/ast.html
- Failure theme (small models omitting declared validation), supporting
  evidence only: `docs/MASTER_EXPERIMENT_PROMPT.md` Part 1, `task_015`.
