# CD-AVC pi extension

Makes the CD-AVC verification loop available inside the pi coding agent, and
lets the agent improve the CD-AVC *harness* itself - under a fixed evaluator
it cannot write to.

## Layout

- `pi_extension/cdavc/index.ts` - the extension:
  - `cdavc_verify` tool: runs the public gates for a dev2 task, returns
    structured feedback. Hidden tests are never exposed through it.
  - write/edit guard: blocks changes to `benchmarks_heldout/`,
    `self_improve/protected/`, any `hidden_tests.py`, and the improvement log.
  - `/cdavc-improve [N]` command: runs N iterations of the self-improvement
    loop in SIMULATED mode (offline, mechanics only, no measurement).
- `self_improve/` (repo root) - the loop itself: bounded config surface,
  proposers, evaluators, controller, offline tests.

## Install

```bash
pi --extension pi_extension/cdavc/index.ts        # one-off
cp -r pi_extension/cdavc ~/.pi/agent/extensions/  # auto-load
```

## The self-improvement contract

1. Editable surface: `self_improve/harness_config.json` only - three knobs
   (`retry_cap`, `prompt_layout`, `lenient_parse`) that map to existing
   BenchmarkRunner arguments. Validation rejects anything else.
2. Fixed evaluator: `self_improve/protected/tasks.json` + the dev2 tests.
   The controller aborts if any protected path differs from git HEAD.
3. Keep-if-better: measured pass count on the fixed task list wins; ties
   break on fewer tokens. Anything else rolls back. Every step is logged in
   `self_improve/IMPROVE_LOG.md` and kept changes are committed.
4. Spend: simulated runs are free and marked "simulated (mechanics only)".
   Live runs are MEASURED, need `--approve-spend --token-cap N`, and are
   never triggered by the extension.
