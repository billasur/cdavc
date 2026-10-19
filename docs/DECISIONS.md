# DECISIONS — product-core

Goal: make CD-AVC a shippable product, not a benchmark harness.

One change per commit. Each entry records **why**, the **alternatives
considered**, and **what it costs**, so a reader can undo any decision
knowing what it was worth. Entries are append-only: a revert is a new
entry, never an edit of an old one.

## Method rules for this branch

- **The benchmark corpus is frozen.** `benchmarks/HELDOUT.sha256` pins the
  30 reported tasks, their test modules and their property table, and
  `tests/test_freeze.py` fails the build if any of them changes or if a
  new file appears under a frozen path. Task statements, hidden tests and
  the held-out property table are never edited — not to fix a failure, not
  to close a property gap, not to make a number look better.
- **Development happens on the dev corpus.** `benchmarks/dev/` holds 40
  disjoint tasks with their own tests, their own reference solutions and
  their own property table, pinned by `benchmarks/dev/MANIFEST.sha256`.
  Every new property, every new gate and every prompt change is developed
  and measured there.
- **The information asymmetry is labelled, never hidden.** `cdavc` may not
  read hidden-test output. The arm that does is named
  `baseline_retry_oracle` and is never presented as the fair comparison;
  the fair comparison is `cdavc` vs `baseline_retry_blind`.
- **A gate that cannot decide says so.** A timeout or an exception inside a
  gate is a `gate_error`, not a rejection. It is counted separately and
  never silently turned into a failed candidate.
- **Every number is labelled** `dev` / `held-out` / `replay`, with the
  model, the sample budget and the confidence interval.

---

## C0 — Bring the measurement infrastructure onto product-core

**Why.** Three things this branch needs did not exist on `plan-90`:
a disjoint dev corpus to develop and measure gates on, a held-out freeze
guard, and a retry arm that does *not* read hidden-test output. Without
the split, "the cage beats retry" would still be a comparison against an
arm that sees the hidden assertions, which is the one comparison this
project must not make.

**Change.** Imported, unchanged and as one commit:

- `benchmarks/dev/` (40 tasks, own tests, references and property table)
  plus `tools/dev_specs.py` and `tools/build_dev_corpus.py`, which refuse
  to emit a task unless its reference passes every test module and its
  property check and the unsolved stub fails the public tests.
- `benchmarks/HELDOUT.sha256` and `tests/test_freeze.py`.
- The `baseline_retry` split into `baseline_retry_blind` (public-test
  output only) and `baseline_retry_oracle` (also receives hidden-test
  output), with the draw budget equalised across sampling arms.

**Alternatives considered.**

- *Keep one retry arm and label it in the report only.* Rejected: the
  arm's prompt would still carry hidden output, so the cage comparison
  would still be asymmetric; a label in prose does not remove the
  asymmetry from the measurement.
- *Write a new dev corpus for this branch.* Rejected: the existing one is
  already hashed, already validated against its own references, and
  writing 40 more tasks would spend the time that the gate work needs.
- *Leave the freeze guard on `plan-95` only.* Rejected: the guard is the
  thing that keeps the held-out number from becoming a fit, and it must
  run in CI on the branch that ships.

**What it costs.** +3 898 lines, of which 3 500 are the dev corpus and its
generator. The dev corpus's properties are differential against a
reference implementation, which is a *stronger* oracle than the held-out
metamorphic checks; a lever that only works because the gate can compare
against a reference does not transfer, and any such result is labelled as
such rather than promoted.

**Measured effect.** 109 tests pass. The held-out corpus and its
property table are byte-identical to `plan-90`.

**Commit.** this commit
