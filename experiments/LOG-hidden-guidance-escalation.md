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
