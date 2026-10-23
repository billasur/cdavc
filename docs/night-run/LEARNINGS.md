# What the night runs taught us

**Date:** 2026-10-24 (summarising work of 19–20 Oct 2026)
**Sources:** `REPORT.md`, `LOG.md`, `experiments/RESEARCH.md` (branch `night-run-v2`),
`docs/DECISIONS.md` + `NEXT_PLAN.md` (this directory), and the measured reports
in `results/` (`REPORT-20-task.md`, `REPORT30.md`, `REPORT50-PAYLOADS.md`).

## The measurement arc

| Run | Model | single | retry | cdavc | best cage arm |
|---|---|---:|---:|---:|---:|
| 20-task dev | Qwen2.5-7B | 60% | **90%** | 85% | — |
| 30-task held-out | Qwen2.5-7B | 53.3% | **80%** | 76.7% | — |
| dev2, 13 harder | gpt-oss-20b | 31% | **62%** | 62% | tie |
| 50-task, v2 harness | Qwen2.5-7B | 58% | **84%** | 72% | `cdavc_sampled` **82%** |

## 1. The retry baseline's headline number was inflated by test leakage

The 20-task run's 90% for plain retry existed because the harness fed the
**failing hidden test's output** into the repair prompt (task_006 literally
received `expected [-3, -2, 0, 0, 4, 9]`). In production no such oracle
exists. The 50-task report makes this explicit in its fairness disclosure:
`baseline_retry` is the only arm that ever sees evaluator output, and with
that advantage it scores 84% vs 82% for `cdavc_sampled` — a 2-point
difference whose CI [-12.5, +8.5] includes zero. **The honest claim is
parity at equal budget, plus integrity guarantees retry cannot offer**
(test-tampering detection, SHA-locked tests, regression, AST contract).

## 2. Output parsing, not model quality, was the biggest recoverable loss

On dev2, 4/13 single-shot answers were unparseable. Of 6 captured raw
failures, the shapes were mundane: a well-formed files object missing its
final `}` (or closing with `]` instead), stray patch-marker text. The lenient
parser recovered 5/6 — one of them (e04) was a **correct solution that had
been thrown away**. → Adopted: the tolerant payload parser now in the v2
harness (`payloads.py`).

## 3. Actionable gate feedback is the one place the cage's design cost points

cdavc failed e04 **three times** on a bare "AST contract failed". With
SyntaxError line/column plus the offending source line, the same model passed
3/3 (e04 in 2 attempts, e10 in 1, e11 in 2), because attempt 2 fixed the
syntax error the line detail exposed. → Adopted: AST-context feedback in the
v2 harness. This was the only measured hypothesis where the cage itself, not
the model, was losing tasks.

## 4. Sampling closes the remaining gap

`cdavc_sampled` (multiple draws behind the cage, equal attempt budget) at
82% [69.2, 90.2] vs retry's 84% [71.5, 91.7] — statistically a tie, with no
evaluator output. `cdavc_sampled_repair` (repair prompts on top of sampling)
added nothing (80%) — consistent with the literature's warning that repair
gains are bottlenecked by feedback quality.

## 5. The cage never hurt, and it is cheap

- Cage-hurt (valid code falsely rejected): **0 measured in every run**
  (0/20, 0/30, mock 30/30). The 9 hidden-gate rejections in the 50-task run
  are candidates that passed public tests but were genuinely wrong.
- Overhead: ~1.7% wall clock over plain retry (20-task measurement), and
  **3.6% fewer prompt tokens** — bounded diagnostics instead of 4000-char
  stack dumps.

## 6. Durable methodology assets

- **Frozen held-out corpus** (`night-run-v2:benchmarks_heldout/`, 30 tasks,
  183-file SHA-256 manifest, references verified under 5 PYTHONHASHSEED
  values) — a real pre-registration; dev decisions never touch it.
- **dev2** with a measured mutation kill rate of **0.928** (219/236 hand
  mutants killed by hidden tests) — evidence the hidden tests are strong,
  not decorative.
- The **one-change-per-experiment protocol** with "prepared, not measured"
  labelling, and the research bibliography (`experiments/RESEARCH.md`) mapping
  each idea to literature (Looping Is Not Reliability, Is Self-Repair a
  Silver Bullet?, Reflexion, Large Language Monkeys, EvalPlus, CodeT,
  TestGen-LLM, Prompts to Properties).

## 7. Tried and rejected — do not re-derive

`NEXT_PLAN.md` SKIP list, all prepared and never measured because dev showed
no failures they could fix: patch-D (arity-aware probe), ast-raise-class
(strict raise-class matching), hidden-guidance-escalation, exp-1 (cumulative
feedback), exp-2 (first-failure-only feedback), plus H-a response_format
(0/8 on allam), H-b prompt layout, more qwen/allam slices (qwen at ceiling).
Designs preserved in `experiments/` here and on `night-run-v2`.

## 8. Highest-value unmeasured experiments (still open)

1. **Fresh-sample control** (`night-run-v2`'s exp-3): retry-with-feedback vs
   fresh independent samples at equal attempts — the Self-Repair-paper
   control that would justify or kill the repair path outright.
2. **Multi-seed statistics** (NEXT_PLAN item 3): arm ordering flipped between
   seeds on the old dev set (6/8, 8/8, 7/8); every headline number so far is
   one seed. Two more seeds × 3 arms ≈ 130K tokens settles the cdavc-vs-retry
   CI.
3. Optional: gpt-oss-120b on dev2 (~25K) to check whether remaining dev2
   failures (e02/e04/e05/e13 — model logic, no pipeline fix identified) are
   a 20B ceiling.
