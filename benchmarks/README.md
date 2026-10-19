# CD-AVC benchmark corpus

This directory contains the fixed, 30-task coding corpus used by the local
benchmark harness. The tasks are original small-to-medium Python exercises
written for CD-AVC in a HumanEval/MBPP style: each task has a short natural
language contract, a public smoke evaluator, a separate held-out evaluator,
and a regression evaluator.

## Source and licence

- Source: original CD-AVC benchmark corpus, version `1`.
- Style reference: HumanEval/MBPP-style function-completion tasks; no task or
  test code is copied from those datasets.
- Licence: repository licence (`MIT`); see [`../LICENSE`](../LICENSE).
- The exact task set and source labels are recorded in
  [`tasks.json`](tasks.json).

The initial implementation files are deliberately incomplete. They are the
starting point for a real local-model run, not answer fixtures.

## Held-out test boundary

`hidden_tests.py` contains the held-out evaluator. It is used to score every
arm but is never included in the model prompt. The prompt contains only the
task description, allowed implementation path, required symbol and public
invariants. The harness also hashes all evaluator files before each task and
checks them again after every cage candidate.

The checked-in hidden evaluator is part of the benchmark definition so the
experiment is reproducible. It must not be edited or tuned after results have
been observed. To create a new benchmark version, copy the corpus, change its
version/source label, and start a new results directory.

## Layout

- `tasks.json` — immutable task manifest and source metadata.
- `tasks/task_NNN/solution.py` — incomplete implementation under evaluation.
- `public_tests.py` — visible smoke evaluator used only by the CD-AVC target
  gate.
- `hidden_tests.py` — held-out scoring evaluator used by all arms.
- `regression_tests.py` — separate deterministic regression gate used by the
  CD-AVC arm.
