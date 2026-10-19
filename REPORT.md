# night-run REPORT (20 Oct 2026, written ~02:45 IST)

**Status: prepared, not measured.** No pass rate was measured overnight. The sandbox cannot host a local model (no LLM endpoint, 1.5 GB RAM, Python 3.10 vs required 3.11+), and the benchmark accepts localhost endpoints only. So nothing here claims an improvement. The REPORT30 numbers (single 16/30, retry 24/30, cdavc 23/30) are unchanged and not re-measured. The 90% goal is not claimed.

## What exists on branch `night-run` (main untouched at 3e54f5d)
- **Held-out set, frozen:** `benchmarks_heldout/` has 30 new tasks (agent1..6, 5 each). `benchmarks_heldout/MANIFEST.sha256` lists SHA-256 for all 183 files; the manifest file itself hashes to 13fbcd07af0c503c626c7daad0d003c112b1301e46535c4a3cc988706468dcaf. `scripts/verify_heldout.sh` checks the manifest, that every reference solution passes public/hidden/regression, and that every stub fails hidden: result 30/30 valid. One reference (task_h401_connected_components) was fixed before the freeze because it was flaky under hash randomization (one-directional edges); tests were not changed. After the fix, all 30 references passed under 5 PYTHONHASHSEED values.
- **Dev set:** `benchmarks_dev/` (agent7..9), 15 tasks. Reference passes and stub fails hidden for all 15 (checked with the same script logic; not under a manifest). Dev drives choices; held-out is only for candidates that beat dev.
- **Experiment branches** (each one change, based on night-run; none measured):
  - `night-run-patch-D`: arity-aware boundary probe (probe is off by default, so an arm must enable boundary_probe)
  - `night-run-patch-ast-diag`: name file/line/symbol in AST-gate failures
  - `night-run-patch-ast-raise-class`: require a raise of the declared exception class, not any raise
  - `night-run-patch-hidden-guidance-escalation`: escalate invariant guidance on consecutive hidden-gate rejections
  - `night-run-patch-exp-1`: latest vs cumulative retry feedback mode
  - `night-run-patch-exp-2`: first-failure-only cage repair feedback
  - `night-run-exp-3`: `baseline_fresh` arm, a fresh-sample control with equal attempts
  Objectives 1-4 from docs/MASTER_EXPERIMENT_PROMPT.md were already implemented, so these target residual gaps. Note: git can't have both `night-run` and `night-run/patch-X`, hence the `night-run-patch-X` names.
- **Docs:** `LOG.md` (all entries, research source URLs in `experiments/RESEARCH.md`), `docs/DECISIONS.md`, `docs/NIGHT_RUN.md`, `experiments/*/PATCH.diff + RATIONALE.md`.

## Measuring on the Mac (same model, same budget for every arm)
```
git fetch origin && git checkout night-run
python3 scripts/make_heldout_tasks.py benchmarks_dev     # builds benchmarks_dev/tasks.json (copies stub -> solution.py)
PYTHONPATH=src python3 -m cdavc.benchmark . --tasks benchmarks_dev/tasks.json --endpoint <your local endpoint> --model <model> --seed 1 --records results/dev-base-s1.jsonl --report results/dev-base-s1.md
```
Repeat for seeds 1, 2, 3. Then `git checkout night-run-patch-<name>` and repeat per branch (one patch at a time; keep the same model, retry cap and timeout). Compare each patch with the baseline using the report's paired difference and Wilson CI. Only for a patch that beats dev: run the same with `benchmarks_heldout` (`python3 scripts/make_heldout_tasks.py benchmarks_heldout`; first run `sh scripts/verify_heldout.sh`), and revert a patch if held-out is worse than dev suggests.

## Honest caveats
- The adapter `scripts/make_heldout_tasks.py` was checked only by running the generated test commands directly (30/30 reference passes, stubs fail hidden). It was **not** run through `cdavc.benchmark` (needs Python 3.11 and an endpoint). Verify with a dry run first; `python` in the commands must resolve on the Mac. Its tasks.json/solution.py are generated, not part of the manifest.
- Dev set was not run through the adapter or the harness either.
- Patch branches have unit tests per their helpers (e.g. D reports 16 pass); I did not re-run them here.
- Task difficulty for the Qwen 7B model is unknown; a task set that is too easy or too hard will not discriminate between arms.
