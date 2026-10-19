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

**Commit.** `f65417c` (code) — this entry was appended afterwards, so the
hash it names is already in history.

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

**Keep or revert.** Keep the split (it is required to report honestly). The
budget equalisation still needs a dev reading before it is kept as a method
change.

**Commit.** `3deface` (code)

---

## D3 — Iterate on a disjoint 40-task dev corpus

**Hypothesis.** A corpus that is disjoint from the reported 30 can expose
levers (selection, repair context, sampling schedule) without turning the
held-out number into a fit. Forty tasks is enough to rank failure modes and
to keep the 3-task noise floor meaningful.

**Change.** `benchmarks/dev/` with 40 single-function tasks, its own public,
hidden and regression modules, a frozen reference implementation per task,
and `benchmarks/dev/properties.json` pinned by `MANIFEST.sha256`.
`tools/build_dev_corpus.py` renders the corpus from `tools/dev_specs.py` and
refuses to emit it unless every reference passes all three test modules and
its property check, and every unsolved stub fails the public tests.
`--properties` and `--only` select the dev table and the per-iteration
subset.

**Known transfer risk.** Dev properties are differential against the
reference implementation, which is a stronger oracle than the held-out
metamorphic checks. A lever that only works because the gate can compare to
a reference will not transfer; any such result is labelled and not promoted.

**Dev result.** n/a — corpus construction. 109 unit tests pass; no model
calls.

**Keep or revert.** Keep.

**Commit.** `46462e6` (code)

---

## D4 — Characterise the dev corpus before any lever (pre-registered)

**Hypothesis.** At the current method, the blind retry arm and the cage are
within 3/40 of each other on dev, and the cage is slower. This establishes
the noise floor and the five hardest tasks used by every later iteration.

**Change.** None — this is a measurement run of all 40 dev tasks with the
current code, 3 draws per sampling arm, seed 20261020.

**Kill criterion.** If the dev corpus is at ceiling for both blind retry and
the cage (>= 38/40 each), it cannot discriminate levers and must be made
harder before any experiment; a set of 5 hardest tasks drawn from a ceiling
corpus is meaningless.

**Dev result.** Pending.

**Keep or revert.** n/a — measurement.

**Commit.** pending
