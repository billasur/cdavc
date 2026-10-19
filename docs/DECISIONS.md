# DECISIONS — plan-95

One change per experiment. Each entry records the hypothesis **before** the
run, what changed, the dev reading, and whether it was kept. Entries are
append-only; a revert is a new entry, not an edit of the old one.

## Method rules for this branch

- **Held-out is frozen.** `benchmarks/HELDOUT.sha256` pins the 30 reported
  tasks, their tests and their property table. It is checked by
  `tests/test_freeze.py`. Held-out failures are not read to choose changes,
  and held-out runs exactly once, after the method is final.
- **Dev is where iteration happens.** `benchmarks/dev/` holds a disjoint
  corpus with its own tests, property table and manifest.
- **Per iteration:** 5 hardest dev tasks (ranked by retry-blind failure rate
  and cage rejections from prior dev runs) + 5 canary regressions. The full
  dev suite runs only at the end of a phase.
- **Equal budget.** `baseline_retry_blind`, `baseline_retry_oracle` and
  `cdavc` receive the same `--samples`, the same seeds and the same base
  prompt contract. `baseline_single` is the 1-draw reference and is never
  used as the fair comparison. `retry_oracle` is the asymmetric arm and is
  always labelled as such.
- **Noise floor.** A dev difference below 3 tasks out of 40 is not signal.
- **Every number is labelled** `dev` / `held-out` / `replay`, with model and
  sample size.

---

## D1 — Freeze the 30 reported tasks before developing against dev

**Hypothesis.** Any pass-rate gain measured after reading held-out failures
is uninterpretable, because the corpus stops being a test set. Freezing the
corpus makes the final number a measurement instead of a fit.

**Change.** Added `benchmarks/HELDOUT.sha256` (sha256 of `tasks.json`, the
three test modules, `properties.json`, all 30 task statements and all 30
reference solutions — 65 files) and `tests/test_freeze.py`, which fails on a
missing file, a changed digest, or an unlisted new file under a frozen path.

**Dev result.** n/a — methodological. The guard passes and the digests match
the corpus as measured for REPORT90.

**Keep or revert.** Keep.

**Commit.** `COMMIT_D1`

---

## D2 — Split retry into blind and oracle arms

**Hypothesis.** REPORT90's `baseline_retry` was handed hidden-test output,
so its 28/30 both measured repair quality and bought information the cage
refuses to look at. Separating the two makes the fair comparison
`cdavc` vs `baseline_retry_blind` and keeps the asymmetric arm visible
instead of hidden inside one number.

**Change.** Two retry arms: `baseline_retry_blind` repairs from public-test
output only; `baseline_retry_oracle` also receives hidden-test output when
the task has a hidden command. Same draw budget, same seeds, same base
prompt.

**Dev result.** Pending — measured on the dev baseline run.

**Keep or revert.** Pending.

**Commit.** `COMMIT_D2`
