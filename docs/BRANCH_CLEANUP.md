# Branch guide: what was cleaned, what stays, what still needs a decision

**Date:** 2026-10-24
**Branch:** `research/flint-and-harness-v2` (HEAD `1d5a2b3`)

Every deletion below was verified lossless before it was made: the deleted
branch's commits are reachable from a ref that stays (`main`, `product-core`,
or `origin/night-run-v2`), or the branch was tagged first. Nothing unique was
destroyed.

## Current state (after cleanup)

| Branch | Where | Status |
|---|---|---|
| `main` | local + `origin/main` | showcase v6 landed; 13 commits of showcase work |
| `research/flint-and-harness-v2` | local only | **the active line.** 3 commits ahead of `main` (v2 harness + night-run doc harvest), 0 behind → fast-forward-able. 213 tests green, full mock smoke done |
| `product-core` | local, worktree at `~/Projects/cdavc-product-core` | 25 commits ahead of `main`, 13 behind. **The one real pending decision** (below) |
| `origin/night-run-v2` | remote | the research evidence archive: frozen held-out corpus (`benchmarks_heldout/`, 184 files + SHA manifest), dev corpus (`benchmarks_dev/`), `LOG.md`, `REPORT.md`, all six experiment designs in `experiments/`, 87 `results/` files |
| `docs/night-run/` | on the research branch | harvested 2026-10-24: `NEXT_PLAN.md` + `DECISIONS.md` (the provenance for the two adopted ideas behind the v2 harness) and the exp-1/exp-2 design docs, which existed only on their branches |
| tags `archive/*` (×10) | local | `plan-95`, `showcase-v5-wip`, `night-run`, `night-run-patch-{D,ast-diag,ast-raise-class,exp-1,exp-2,hidden-guidance-escalation}`, `3d-story-v2` — full insurance for every branch deleted below; delete tags individually once you're confident |

## What was deleted, and why it was safe

| Deleted | Kind | Evidence of losslessness |
|---|---|---|
| `showcase-v6` (local) | branch | pointed at `79bd2ec`, the exact commit `main` and `origin/main` are on |
| `plan-90` (local) | branch | all 10 commits are ancestors of `product-core` |
| `plan-95` (local) | branch | 10 commits ancestral to `product-core`; the other 4 landed there as `15b27b9` ("Bring the dev corpus, the freeze guard and the blind/oracle retry split") — 0 files in plan-95's tree absent from product-core's; head also tagged `archive/plan-95` |
| stash `v5-wip` | stash | tagged `archive/showcase-v5-wip` before dropping; showcase v6 landed anyway |
| `refs/codex/turn-diffs/*` (×2), `refs/freebuff/*` (×6) | editor checkpoint refs | editor session scratch; the freebuff refs pointed at plan-95 commits (kept via tag/product-core). These refs were the **only** thing keeping the 94 MB `submission_video.mov` blob and the large `.ogcode` DB blobs pinned in `.git` |
| `origin/3d-antigravity`, `origin/showcase-v6` | remote branches | ancestors of `origin/main` |
| `origin/night-run-dev2`, `-exp-3`, `-exp-4`, `-lenient` | remote branches | ancestors of `origin/night-run-v2`, which stays |
| 9 stale worktree entries (temp benchmark dirs) | worktree metadata | `git worktree prune`; directories were already gone |

## Step 1 — merge the research line into main (executed 2026-10-24)

`research/flint-and-harness-v2` was fast-forwarded into `main` and pushed
(through `40d3f69`); the branch is deleted. `main` is the active line.

All subsequent work (including the LEAN_AUDIT P0–P3 phases) then happens on
short-lived branches off `main`.

## Step 2 — the one real decision: `product-core`

`product-core` carries ~23 commits that exist **nowhere else**: the product
surface ("profiles, one command, one verdict"), the differential gate, the
dev corpus with freeze guard, the blind/oracle retry split, offline benchmark
CI, and the honest measured reports. It overlaps the research branch on 10
files (`benchmark.py`, `cli.py`, `properties.py`, `providers.py` + tests),
which is exactly the duplication LEAN_AUDIT F1 wants collapsed into one
`AttemptLoop`.

**Do not delete `product-core`.** Choose one:

- **Reconcile (recommended, matches the YC "deterministic pre-merge gate"
  positioning):** rebase or merge `product-core` onto the new `main`, then do
  audit phase P1 (extract the shared attempt loop) so both surfaces drive one
  loop. The benchmark then measures the shipped system.
- **Harvest:** if the research line supersedes it, cherry-pick the product
  commits that still matter (product surface, differential gate, dev corpus)
  onto `main`, then tag `archive/product-core` and delete.

Until that's done, keep working in the `~/Projects/cdavc-product-core`
worktree or merge carefully — the two lines will keep diverging.

## Step 3 — remote verdicts (executed 2026-10-24, after content inspection)

Each deleted branch was fetched and inspected first; every one is preserved
by a local `archive/*` tag:

| Branch deleted | Verdict | Evidence |
|---|---|---|
| `origin/night-run` | harvest-then-delete | its 6 unique commits were docs only: `DECISIONS.md` final entries + `NEXT_PLAN.md`, both copied to `docs/night-run/` (commit `c18c586`) |
| `origin/night-run-patch-D` / `-ast-diag` / `-ast-raise-class` / `-hidden-guidance-escalation` | waste | design (`PATCH.diff` + `RATIONALE.md` + log entry) already archived in `night-run-v2`'s `experiments/` tree; all four explicitly marked SKIP in `NEXT_PLAN.md`; the adopted ideas (lenient parsing, AST-gate detail) already landed in the v2 harness |
| `origin/night-run-patch-exp-1` / `-exp-2` | waste after harvest | both marked SKIP; their design docs were the only copies, now in `docs/night-run/experiments/` |
| `origin/3d-story-v2` | waste | earlier scroll-story showcase iteration; superseded by the showcase v6 that landed on `main`; its `?debug` hook never landed |

`origin/night-run-v2` stays as the sole remote archive. If you ever delete it
too, first copy out `REPORT.md`, `LOG.md`, `benchmarks_heldout/` (the frozen,
manifest-hashed pre-registration corpus), and any `results/` you cite — that
corpus is the raw evidence behind the v2 numbers.

## Step 4 — reclaim the disk (executed 2026-10-24)

After backing up `.git` to `/tmp/git-backup-20261024`, reflogs were expired
and `git gc --prune=now` run: **`.git` went from 146 MB to 11 MB.** The
untracked `.ogcode` databases are now gitignored (commit `92a50af`), so the
every-run churn is gone.

Two tracked `.ogcode/ogcode.db` files (32 MB) remain reachable from `main`'s
tree — only a `git filter-repo` pass removes them from history (LEAN_AUDIT
F7/P4). Do the P0 `git rm --cached` + `.gitignore` fix regardless; it stops
the churn in every future commit.

## What not to touch

- `main`, `product-core` (until Step 2 is decided), `origin/night-run-v2`
  (sole research evidence archive).
- Tags `archive/*` — they cost nothing and are the only anchor for their
  histories.
