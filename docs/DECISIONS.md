# DECISIONS (night-run, 20 Oct 2026)

Format: time (IST) - decision - why - alternatives.

- 02:24 - Work only on branch `night-run`; never touch main or SPL repos. Why: user rule. Alternative: PRs from per-experiment branches (kept as `night-run-patch-X` branches for patches, merged only via lead).
- 02:24 - Held-out set of 30 NEW tasks, frozen with SHA-256 manifest, checked only for candidates that beat dev. Why: avoid overfitting to the dev set. Alternative: reuse the 30 existing tasks (rejected: already seen).
- 02:24 - One change per experiment, 3 seeds, Wilson CI, revert on overfit, same sample budget and stdlib line for all arms. Why: user rules.
- 02:24 - Sandbox cannot host the original Qwen2.5-7B (1.5 GB RAM, 2 CPUs, no LLM key; benchmark accepts localhost endpoints only). Runs by agents use a different model and are labelled NOT comparable to REPORT30. Why: pipeline is BYOM, approval relayed by the main agent at 02:24, not independently verified by this agent. Unmeasured items say "prepared, not measured".
- 02:25 - Per-task records for REPORT30 are not in the repo; analysts work from docs/MASTER_EXPERIMENT_PROMPT.md and code. Objectives 1-4 from that doc were found already implemented, so analysts targeted residual gaps instead. Alternative: re-implement (rejected, duplicate).
- 02:25 - Held-out domain split across writers 1-6: strings/parsing, dates/time, math/number theory, collections/graphs, text formats/validation, state machines/iterators; 5 tasks each in benchmarks_heldout/agentN/. Why: avoid collisions and duplicates.
- 02:27 - Added dev-set writers 7-9 under benchmarks_dev/ (a dev set separate from held-out, so dev results drive choices). Added experiment-patch helpers 1-4 (branches night-run-patch-X). Helper IDs for the record: patches agent-01M5AZ8TWE5BMWAN12RZ1XJVNN, agent-01M5AZ8W1GZZTW8EQ82Q8WJH2K, agent-01M5AZ8X0HEHH2VGC3P0S4JNSP, agent-01M5AZ8Y2DM4273P00WE374GPA; dev writers agent-01M5AZ8Z6ZR17TKWKA5ZY31K7K, agent-01M5AZ9074YY904ASFD4SD96BD, agent-01M5AZ91AHV6QQHSMGT9Q1M8DW.
- 02:27 - Lead (this agent) does freeze, integration, LOG.md, REPORT.md, and makes routine calls without asking the user (instruction relayed by the main agent at 02:27).
