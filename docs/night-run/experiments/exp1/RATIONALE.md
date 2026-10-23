# exp1: latest-trace-only vs cumulative retry feedback (prepared, not measured)

Full entry: `experiments/EXP1.md` (hypothesis, sources, measurement protocol).

Summary: the benchmark already fed only the latest failure trace to retry prompts; this patch adds the missing cumulative arm as `--feedback-mode {latest,cumulative}` on the `baseline_retry` arm only, records the mode in every JSONL record, and guards resume against mixing modes. The `cdavc` arm stays latest-only because its hidden-gate categorisation parses a single failure's first line. One change, same attempt budget in both modes. Unit tests (5 new) pass under Python 3.10 in the sandbox; re-run under 3.11+ on the Mac before measuring.
