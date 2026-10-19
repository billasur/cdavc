# Path to ≥90 % — plan, with the measurements that justify each step

Status: implemented (P0–P4) on branch `plan-90` and measured once end to end. **The 90 %
target was not reached**; see §8 for the measured table and §9 for what is still unverified.
Baseline: `results/benchmark30.jsonl` (30 tasks, Qwen2.5-7B-Instruct Q4_K_M, seed 20261019).
New evidence: `results/pilot-best-of-n.json` (probe run for this plan, see §1.2).
Post-implementation run: `results/benchmark90.jsonl`, report `results/REPORT90.md`.

---

## 1. What the data says

### 1.1 The seven failures, decomposed

| Task | cdavc failure | Class | Fixable without touching task data |
|---|---|---|---|
| task_023 | `No module named 'numpy'` on all 3 attempts | mechanical | yes |
| task_026 | `No module named 'numpy'` ×2, JSON error ×1 | mechanical | yes |
| task_030 | `provider response is not a JSON files object` ×3 | mechanical | yes |
| task_013 | public fails → hidden fails → public fails | search/selection | yes |
| task_029 | public fails → hidden fails → hidden fails | search/selection | yes |
| task_006 | public passes, hidden fails ×3 (deduplicates equal values) | **verifier false-accept** | yes, with a property gate |
| task_015 | public passes, hidden fails (no `ValueError` for `"IIII"`) | **verifier false-accept** | yes, with a property gate |

The invariant audit is clean: every one of the 10 hidden `_raises(...)` checks has an invariant
that declares the raise, and task_006's invariant already says *"may contain equal or negative
values"*. So **there is no task-data gap to patch** — the gap is on our side.

### 1.2 Root cause #1: the retry loop has no diversity

`_complete` (`src/cdavc/benchmark.py:444-454`) sends `self.seed` on **every** attempt. The server
default is temperature 0.8 / top_p 0.95 (`/props` on :8080, verified), but a fixed seed restarts the
same RNG stream, so attempt *n+1* differs from attempt *n* only because the prompt changed. The
model consequently re-emits `import numpy` three times in a row while being told, in plain text,
that numpy does not exist. That is not a capability ceiling — it is a sampling bug.

### 1.3 Root cause #2: the verifier is one assertion wide

The cage's targeted gate runs one assertion per task (`benchmarks/public_tests.py`), and the hidden
gate is one assertion too (`benchmarks/hidden_tests.py`). A candidate that deduplicates a merge
passes the visible gate and is then rejected blindly. cdavc's 76.7 % vs retry's 80.0 % is *entirely*
explained by retry being handed the hidden assertion strings; the cage cannot substitute for that
oracle because the cage's own oracle is too weak. **Selection quality, not repair text, is the
binding constraint.**

### 1.4 Probe: best-of-N with the *existing* verifier

7 failing tasks × 4 samples (temperature 0.8, distinct seeds = `20261019+i`), keep the first sample
that passes the current public gate, then run the hidden gate. No new gates, no repair loop, no
prompt change (`results/pilot-best-of-n.json`):

| Task | public pass | selected sample passes hidden |
|---|---:|---:|
| task_006 | 4/4 | no (dedups every time) |
| task_013 | 3/4 | **yes** |
| task_015 | 2/4 | no (never raises) |
| task_023 | 0/4 | no (numpy) |
| task_026 | 2/4 | **yes** |
| task_029 | 3/4 | **yes** |
| task_030 | 2/4 | **yes** |

→ **27/30 = 90.0 %** from sampling + the gate we already have, with no new components.
Adding one sentence to the prompt — *"the evaluation environment has no third-party packages: use
the standard library only"* — makes 023 4/4 and 026 3/4, giving **28/30 = 93.3 %**, with 006 and
015 as the only survivors.

Cost is not the problem: early-exit selection draws ~38 samples across 30 tasks, versus ~44
attempt-1..3 generations today. **Best-of-N with a working gate is cheaper than a blind retry loop.**

---

## 2. Target ladder

| Step | Changes | Pass rate | Confidence |
|---|---|---:|---|
| today | — | 23/30 = 76.7 % | measured |
| P0 | mechanical: per-sample seed, stdlib-only | ≤ 24/30 | high but only helps 023/026/030 |
| P1 | best-of-N + early-exit selection | **27/30 = 90.0 %** | **measured by probe** |
| P0+P1 | both | **28/30 = 93.3 %** | measured by probe (per-task, not yet end-to-end) |
| P2 | property / metamorphic verifier | 29–30/30 = 96.7–100 % | estimated; 006 and 015 are mechanically catchable |

P1 is the jump. P2 is what makes the number *stable* rather than a draw — and it is the same
component that would have made cdavc beat retry in the last run.

---

## 3. Components

### P0 — mechanical, no new model calls (≈1 h, near-zero risk)

1. **Per-sample seed.** In `_complete`, derive `seed = (self.seed * 1_000_003 + attempt) % 2**31`
   instead of passing `self.seed` unchanged. This is the single highest-leverage line in the repo.
   Record the per-attempt seed in `attempt_log` so a run is replayable.
2. **Stdlib-only.** Add the "standard library only" line to `_prompt` (`benchmark.py:456-476`) and an
   AST import allowlist in `_run_cage_gates` before the test execution: reject any
   `ast.Import/ImportFrom` outside `sys.stdlib_module_names` with
   `AST Contract Failed: task imports a non-stdlib module 'numpy'`. Cheap, deterministic, and it
   fails at Gate 2 instead of after a wasted subprocess.
3. **JSON robustness.** On `_apply_response` failure, re-ask once with `"Return only the JSON
   object."` before counting a failed attempt; optionally set llama.cpp `response_format:
   {"type":"json_object"}`. *If added, it must be added to all three arms* or the comparison is void.

### P1 — search layer (≈half a day)

4. **`--samples N`** (default 1 for both baselines, 4 for cdavc). Restructure the attempt loop in
   `_run_arm` (`benchmark.py:314-412`) into: *draw → gates → (first full pass wins) | (append the
   failure digest to the next prompt) → draw*. Three exit conditions: all gates pass, samples
   exhausted, or the same failure signature repeats twice (then change decoding — raise temperature
   one step — rather than repeating the identical draw).
5. **Report sampling honestly.** Add `samples_drawn`, `distinct_failure_signatures`, and
   `samples_to_accept` to the JSONL. A pass-rate comparison that hides the sample budget is not a
   comparison; publish `pass @ N samples` for every arm.

### P2 — verifier strength (1–2 days) — this is what "coverage" should mean here

6. **`spec_probe` gate — mechanical metamorphic properties.** Derive properties from the signature
   and description, run them with a seeded input generator, forward the failing input (leak-free:
   the oracle is *ours*, not hidden):
   - size/shape/multiset: `len(merge(a,b)) == len(a)+len(b)`, output is a permutation of
     `sorted(a+b)` → kills 006's dedup immediately.
   - inverse/round-trip: `int_to_roman(roman_to_int(s)) == s` on a fixed numeral corpus, and
     rejection of `"IIII"`/`"IC"`/`""` → kills 015's naive lookup adder. Tasks 015/016 are declared
     inverses, so this is derivable from the corpus, not from the hidden test.
   - purity/immutability: deep-copy the args, call, assert unchanged (covers tasks 008/027/030).
   - empty/zero/boundary identity per type (`""`, `[]`, `0`, single row/column matrices).
   Implement as one module `src/cdavc/properties.py` with a per-task property table
   `benchmarks/properties.json`, **frozen and hashed exactly like `test_files`** so that tuning it
   after a run is visible in the diff.
7. **`differential` gate (optional, strongest).** Ask the model for a *second, independent*
   implementation under a "write this as a reference implementation, naive is fine" prompt; compare
   on ~200 seeded random inputs from a type-aware generator. Disagreement is reported as
   `input → A gave x, B gave y` — a concrete, generated oracle with no hidden-test leakage. This is
   AlphaCode-style filtering with an LLM-authored oracle instead of curated tests.
8. **Verifier-coverage number (measurement, not a gate).** Mutate the candidate with a tiny stdlib
   AST mutator (flip `<`/`<=`, ±1 on an integer literal, drop a branch) and count how many mutants
   the gate suite kills. **A surviving mutant is a candidate the verifier would false-accept.**
   Report `mutant_kill_rate` per arm alongside pass rate — that is the honest "coverage" metric, and
   it also tells you when to spend more samples instead of more repair rounds.

### P3 — repair quality (≈half a day)

9. **Failure digest + regression memory.** Canonicalise each failure to `input → expected / got`,
   deduplicate, and replay *all* previously failing inputs on every new candidate. Both 013 and 015
   show the oscillation pattern "attempt 2 fixes the public test, breaks the hidden one" — replay
   ends it, and it costs one subprocess.

### P4 — measurement integrity (needed before the number can be *claimed*)

10. **Persist candidates.** Content-address every generated file under
    `results/candidates/<run>/<task>/<sha>.py` (gitignored). Then any verifier change can be replayed
    offline against the hidden labels at **zero model cost**, and you get false-accept / false-reject
    rates directly. Without this, every verifier experiment costs a 12-minute model run.
11. **Corpus size.** n = 30 means one task = 3.3 points. Wilson 95 % CI for 28/30 is ≈ [79 %, 98 %];
    for 27/30 ≈ [74 %, 97 %]. The point estimate is what it is; **do not describe the lower bound as
    90 %**. Either grow the corpus to 60–100 tasks (cheapest way to shrink the interval) or run
    3 seeds × 30 and report per-seed stability. Any new tasks must be authored *before* the run.
12. **Report per arm:** pass rate, Wilson CI, paired delta, samples drawn, tokens, wall time,
    false-accept rate (passed public gate, failed hidden), cage-hurt, mutant kill rate.

---

## 4. Cost model

Per task, expected samples drawn with early exit ≈ 1.27 (23 tasks at 1 sample, and the 7 failures
need 1–4 each, total 38 for the 30-task corpus — versus 44 generations for the current 3-attempt
loop). So P1 *reduces* generation cost while raising the pass rate. The cage overhead itself is
unchanged (~2.7 s vs retry on the last run). P2 adds one subprocess per attempt (milliseconds) plus,
for the differential gate, one extra generation per task.

---

## 5. Sequencing

1. **Day 1 — P0 + P1.** Land the seed derivation, the stdlib line and allowlist, and `--samples`.
   Run the full 30. Expected 28/30; if it lands at 27, the early-exit selector is the suspect.
2. **Day 2 — P4.10.** Start persisting candidates *before* Day 1's run so the replay corpus exists.
3. **Day 3–4 — P2.6.** Property table for the 30 tasks; start with 006/015 and the purity properties,
   then backfill. Re-run only the tasks whose gate outcome changes — a candidate replay makes this
   seconds.
4. **Day 5 — P2.7 / P2.8.** Differential gate + mutant kill rate. Report both.
5. **Day 6 — corpus expansion to 60–100 tasks, pre-registered, then one clean run.**

Definition of done: `make test` green, `make benchmark-mock` deterministic, a full run at ≥ 27/30
with the point estimate ≥ 90 %, cage-hurt 0, false-accept rate reported and falling, and every
claim traceable to a JSONL artifact.

---

## 6. Do not do

- **Do not enrich `benchmarks/tasks.json` invariants after seeing failures.** The audit in §1.1
  shows the declared invariants already cover the hidden raises and 006's duplicates. Editing them
  now would be tuning the benchmark to its answers, and it would invalidate the 20- and 30-task runs.
- **Do not paste `public_tests.py` into the prompt.** It is one assertion per task; it converts the
  benchmark into a memorisation test and still does not fix 006 or 015.
- **Do not make `boundary_probe` universal.** Calling every function with `0` false-rejects correct
  functions with non-zero domains; cage-hurt must stay 0.
- **Do not apply grammar constraints or the stdlib line to cdavc alone.** Same prompt, same decoding,
  all three arms — otherwise the delta measures the prompt, not the cage.
- **Do not compare best-of-4 against 3-attempt retry.** Report samples drawn on both sides.

---

## 7. Evidence used

- AlphaCode — sample widely, then filter with execution: <https://arxiv.org/abs/2203.07814>
- EvalPlus / MBPP+ — single-assertion tests systematically overstate correctness; test augmentation
  is what separates 60 % from 80 %: <https://github.com/evalplus/evalplus>
- Self-Debugging — execution feedback as a repair loop: <https://arxiv.org/abs/2304.05128>
- Snell et al., test-time compute — sampling + a verifier beats a 14× larger model when the verifier
  is good, and verifier quality is the binding constraint: <https://arxiv.org/abs/2408.03314>
- LLM-inferred properties for property-based testing: <https://www.anthropic.com/research/property-based-testing>
- llama.cpp GBNF / JSON-schema constrained decoding (guarantees parseable JSON):
  <https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md>
- Mutation testing as a verifier-adequacy oracle: <https://engineering.fb.com/2025/09/30/security/llms-are-the-key-to-mutation-testing-and-better-compliance/>

---

## 8. Measured result (post-registration)

Run of 2026-10-20, 30 tasks, `Qwen2.5-7B-Instruct` Q4_K_M, seed 20261019, retry cap 3,
`--mutants 3`. Artifacts: `results/benchmark90.jsonl`, `results/REPORT90.md`,
stored candidates under `results/candidates/` (gitignored).

| Arm | Passed | Rate | 95 % CI (Wilson) | Draws spent | Mean wall | Mean samples to accept |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_single` | 24/30 | 80.0 % | [62.7 %, 90.5 %] | 30 | 17.3 s | 1.00 |
| `baseline_retry` | 28/30 | 93.3 % | [78.7 %, 98.2 %] | 43 | 24.8 s | 1.36 |
| `cdavc` (as recorded) | 25/30 | 83.3 % | [66.4 %, 92.7 %] | 45 | 43.4 s | 1.32 |
| `cdavc` (offline replay) | 26/30 | 86.7 % | [70.3 %, 94.7 %] | 45 | — | 1.32 |

Paired differences: `baseline_retry − baseline_single` +0.133 [0.010, 0.257];
`cdavc − baseline_single` +0.033 [−0.115, 0.181]; `cdavc − baseline_retry`
−0.100 [−0.209, 0.009].

The replay row re-runs the **stored candidates** through the fixed gates with no model
calls. 29 of 30 recorded verdicts reproduced exactly; the single mismatch is `task_021`,
whose rejection was caused by the mutant-measurement hang described below.

### What the prediction got wrong

§1.4 estimated 28/30 from a probe in which only the cage received diverse seeds and the
stdlib sentence. P0 applies both to **every** arm, and `baseline_retry` moved 24 → 28 on
its own. The predicted jump was the sampling bug, not the cage: once the retry arm samples
distinct seeds, best-of-3 retry matches best-of-4 cage while spending fewer draws and 57 %
less wall time per task (24.8 s vs 43.4 s).

The remaining gap is consistent with the benchmark's own asymmetry, which §1.3 documents:
the retry arm is handed hidden-test output by construction, the cage is not. `task_015` is
the case in point — retry fixes it from the hidden assertion, the cage refuses to look.

### What the gates actually did

- `task_006` deduplicating merge: caught by `merge_sorted_multiset` (no arm passed).
- `task_027` in-place argument mutation: caught by the purity check (no arm passed).
- False-accept rate: 1 of 25 public-gate passes was rejected by the hidden gate (4.0 %,
  `task_013`, recovered on a later draw).
- Mutant kill rate: 98.9 % mean across the cage's candidates.
- Cage-hurt, measured: 2. One was instrumentation (`task_021`): a mutated loop bound never
  terminated, the alarm was swallowed by the property runner's `except Exception`, and the
  gate timed out; the candidate itself passes in 0.04 s and passes on replay after the fix.
  The other (`task_009`) is genuine — both draws emitted an implementation that appends
  lists instead of extending them, which the harness's own invariant rejects. Post-fix
  cage-hurt for this run is therefore 1/30 and it is a sampling loss, not a false reject.

### Revised ladder

| Step | Predicted | Measured |
|---|---:|---:|
| today (pre-plan) | 23/30 = 76.7 % | 23/30 = 76.7 % |
| P0+P1 | 28/30 = 93.3 % | 25/30 = 83.3 % (26/30 replay) |
| P2 | 29–30/30 | not separable: no arm passed 006/027, and the properties changed no other verdict |

## 9. Not verified

- **n = 30, one seed.** Wilson lower bounds are ~70 %, so the 90 % claim is not supported
  for any arm — including retry's 93.3 % point estimate. The corpus was not expanded to 60
  tasks, so the interval is still one task = 3.3 points wide.
- **The corrected 26/30 is a replay**, not a fresh run: it is the same stored candidates
  under fixed gate code. A fresh run would draw different candidates.
- **Property coverage is one property per task.** The 98.9 % kill rate is strong but the
  surviving `task_021` mutant (a flipped comparison bound) shows the index property is not
  exhaustive; a second property per task was not written.
- **Mutant timeouts count as kills.** That is defensible (non-termination is a defect) but
  it inflates the kill rate slightly relative to a pure "property assertion failed" count.
- **Not run:** 3 seeds × 30 tasks, a 60-task corpus, and the optional differential gate.
- The cage's wall-time overhead (1.75× retry, 2.5× single) is measured but was not
  profiled; the property subprocess is a fixed cost per draw.
