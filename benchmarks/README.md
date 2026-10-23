# CD-AVC benchmark corpus

This directory contains the fixed, 50-task coding corpus used by the local
benchmark harness. The tasks are original small-to-medium Python exercises
written for CD-AVC in a HumanEval/MBPP style: each task has a short natural
language contract, a public smoke evaluator, a separate held-out evaluator,
and a regression evaluator.

## Source and licence

- Source: original CD-AVC benchmark corpus, manifest version `2`; individual task source labels retain their original versions.
- Style reference: HumanEval/MBPP-style function-completion tasks; no task or
  test code is copied from those datasets.
- Licence: repository licence (`MIT`); see [`../LICENSE`](../LICENSE).
- The exact task set and source labels are recorded in
  [`tasks.json`](tasks.json).

The initial implementation files are deliberately incomplete. They are the
starting point for a real local-model run, not answer fixtures.

## Held-out test boundary

`hidden_tests.py` contains the held-out evaluator. It scores the selected
artifact once after public selection ends. A hidden failure cannot request or
select another candidate, and hidden output never enters a repair prompt.
Implementation source and explicitly published `context_files` are retrievable;
merely hash-locking an evaluator does not publish it as model context.

All arms use the same initial prompt and final evaluator. Records distinguish
public acceptance from held-out success. Every check protects evaluator/candidate
content and runs in fresh state. Retry/draw budgets still differ between arms;
these results are not automatically matched-token comparisons.

The checked-in hidden evaluator is part of the benchmark definition so the
experiment is reproducible. It must not be edited or tuned after results have
been observed. To create a new benchmark version, copy the corpus, change its
version/source label, and start a new results directory.

## Layout

- `tasks.json` — immutable task manifest and source metadata.
- `tasks/task_NNN/solution.py` — incomplete implementation under evaluation.
- `public_tests.py` — visible smoke evaluator used for public selection in every arm.
- `hidden_tests.py` — held-out scoring evaluator used by all arms.
- `regression_tests.py` — separate deterministic regression gate used by the
  CD-AVC arm.

`verifier_fixtures.json` is a separate, constructed adversarial diagnostic for
property-checking behaviour, not a modification to the 50-task scoring corpus.
See [`../docs/VERIFICATION_ROADMAP.md`](../docs/VERIFICATION_ROADMAP.md).
