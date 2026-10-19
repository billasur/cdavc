# RATIONALE - hidden-guidance-escalation

Status: prepared, not measured.

## Assignment check

Objective 2 of docs/MASTER_EXPERIMENT_PROMPT.md (invariant-anchored semantic
guidance on hidden failure) is already implemented on night-run:
`_cage_repair` routes hidden-gate failures to `_invariant_guidance`, which
restates the contract's declared invariants and a generic edge-case line
(src/cdavc/benchmark.py, night-run). This patch is therefore the next single
change on the same theme that the current code still lacks.

## The one change

When the hidden gate rejects two or more consecutive repairs for the same
task, the guidance keeps the invariant checklist and appends a strategy-shift
block ("Repeated hidden-gate rejection: ... rebuild from the specification ...
trace by hand on one input per edge-case category"). Today the model receives
byte-identical guidance on every hidden rejection.

Code: `_run_arm` computes `_consecutive_hidden_failures(attempts)`; `_prompt`
and `_cage_repair` forward it; `_invariant_guidance(task, escalate=...)`
appends the block. No gate semantics, gate order, or leakage policy changes.
Patch branch: night-run-patch-hidden-guidance-escalation (a
`night-run/patch-*` ref cannot exist next to the `night-run` branch in git).

## Evidence from this repository

- results/REPORT30.md: cdavc arm 23/30 (76.7%), baseline_retry 24/30. Seven
  cage-failure cases; per-task records are not in the repo.
- .ogcode/memory/2026-10-19T193723Z--ses01M5ARMDHDNA--cd-avc-verification-cage-upgrade-30-task-benchmark.md:
  task_013 and task_029 - "the cage now forwards the public failure text for
  these (it did, on attempt 1), yet the model still misses the hidden gate at
  attempts 2-3." Both attempts 2 and 3 received the same guidance text.
- Same note, decisions: task_006 and task_013 invariants under-describe their
  hidden tests - task-data work, deliberately out of scope for a cage patch.

## Hypothesis

A small local model anchored on its previous candidate reads identical
repeated feedback as "keep patching", so attempt 3 tends to be a minimal edit
of attempt 2. An explicit strategy-shift directive on the second consecutive
hidden rejection (rebuild from spec and invariants, then hand-trace one input
per edge-case category) adds new, leak-free signal and should convert some
attempt-2/3 stalls into passes. The added text is generic strategy plus the
contract's own invariants, so hidden assertions still cannot leak and
cage-hurt stays 0 by construction (gates are untouched).

This matches published findings: LLMs do not self-correct from identical
internal feedback alone (Huang et al. 2023), while explicit verbal
reflection on a failure changes the next attempt's behavior (Shinn et al.
2023). The patch supplies the cheapest deterministic version of that
reflection prompt, gated to fire only on a measured repeat failure.

## Validation performed

- Unit suite on the patch branch, Python 3.10.12 sandbox (repo targets
  3.11+, so this is indicative only): 68 tests; the only error is
  tests/test_launch.py memory auto-detection, which errors identically on
  unmodified night-run in this sandbox (host has less RAM than the test
  model's reserve). New test
  test_cage_escalates_invariant_guidance_on_repeat_hidden_failure passes and
  asserts: first hidden repair has no escalation, second does, invariants
  still present, hidden assertion secret never in any prompt.
- Mock benchmark (--mock, seed 0, same flags as `make benchmark-mock`, run
  directly because check-python requires 3.11): 30/30 all three arms, 0
  cage-hurt, matching results/REPORT-mock.md. Mock passes on attempt 1, so
  the escalation branch never fires; deterministic CI behavior is unchanged.
- Effect on the real-model 30-task benchmark: prepared, not measured. It
  needs the Qwen2.5-7B-Instruct run on the M3 Air (command in
  docs/MASTER_EXPERIMENT_PROMPT.md Phase 3). Any numbers I could produce here
  would come from scripted providers, not Qwen, and are not comparable to
  results/REPORT30.md.

## Risks and costs

- Prompt tokens: the escalation block adds about 60 tokens to a repair prompt,
  only on the second and later consecutive hidden rejections (in the REPORT30
  run shape, at most the 3rd attempt of already-failing tasks). Small but
  real; compare token columns against REPORT30 with this in mind.
- If escalation text itself becomes repetitive on attempt 4 (same text again),
  that is accepted: retry-cap 3 bounds it to at most two sends per task.

## Sources (URLs verified live 2026-10-20)

- https://github.com/billasur/cdavc/blob/night-run/src/cdavc/benchmark.py
- https://github.com/billasur/cdavc/blob/night-run/results/REPORT30.md
- https://github.com/billasur/cdavc/blob/night-run/docs/MASTER_EXPERIMENT_PROMPT.md
- https://github.com/billasur/cdavc/blob/night-run/.ogcode/memory/2026-10-19T193723Z--ses01M5ARMDHDNA--cd-avc-verification-cage-upgrade-30-task-benchmark.md
- https://arxiv.org/abs/2310.01798 (Huang et al., Large Language Models Cannot Self-Correct Reasoning Yet)
- https://arxiv.org/abs/2303.11366 (Shinn et al., Reflexion: Language Agents with Verbal Reinforcement Learning)
