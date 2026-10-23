# Verification harness: P0–P4

This implementation separates generating a candidate, accepting it under public
checks, and scoring it against held-out tests. An acceptance is evidence about
the declared checks, not a proof of correctness or a security certification.

## Implemented boundaries

| Priority | Behaviour | Regression evidence |
|---|---|---|
| P0 | Public selection ends before held-out scoring; held-out failure cannot request another candidate. | `test_hidden_failure_never_requests_another_candidate_in_any_arm` |
| P0 | Every dispatched provider call has a receipt, including failures, JSON re-asks and context retrieval. Unknown usage never becomes a zero or complete total. | `tests/test_accounting.py`; benchmark mixed-usage and call-budget tests |
| P0 | Resume fingerprints cover the frozen source snapshot, evaluator inputs, engine code, Python version, task definitions, seed, declared model metadata, budgets and context configuration. | Resume rejects changed source, limits and metadata; identical CLI commands resume with default or custom report paths. |
| P1 | CLI, benchmark and exported artifacts use `verification.py`; each candidate/check repetition uses fresh filesystem state. | Accepted and inconclusive CLI/benchmark evidence parity, poison-file isolation and evaluator-mutation tests |
| P1 | Candidate bytes, contracts and evidence have content digests; existing corrupt objects fail closed. Publication preserves verified UTF-8 bytes, including CRLF. | Artifact-tampering, self-modification and exact-publication tests |
| P2 | Whole-file replacements and original-coordinate exact edits preflight every target before writing. Ambiguous, overlapping, stale and out-of-contract edits fail without partial application. | `tests/test_edits.py`, supervisor invalid-second-edit test |
| P2 | Deterministic source chunks have verified digests and retrievable IDs. Search covers omitted chunks, including under the smallest supported budget. | `tests/test_context.py`, end-to-end tail-context retrieval test |
| P3 | Explicit runtime properties check actual values/exceptions and optional input non-mutation. Repeated conflicting verdicts are inconclusive, not accepted. Empty test runs do not count as verification. | Property, flake and empty-suite tests; frozen diagnostic below |
| P4 | JSON, exact edits and strict textual diffs from any labelled source use the same verifier. Comparisons require compatible snapshots/contracts/configuration and disclose upstream telemetry limits. | `tests/test_adapters.py`, `tests/test_patches.py`, CLI export/compare tests |

## Core data flow

1. Freeze a `WorkspaceSnapshot`, excluding private/hidden directories, caches,
   `node_modules`, managed artifact/result directories and planned output files.
   Ordinary JSONL input data is retained. Snapshot directories and file modes
   are recorded; symlinks are rejected rather than followed outside the project.
2. Materialize a fresh candidate workspace. A rejected candidate's extra files,
   imported modules and test side effects cannot poison a subsequent candidate.
3. Apply the complete payload transactionally with `apply_candidate`.
4. Extract the exact UTF-8 candidate bytes into a content-addressed artifact.
5. Run one `VerificationContract`: evaluator integrity, Python syntax/symbols,
   the legacy coarse exception-presence guard, optional boundary probe,
   targeted/negative/regression commands, and explicit executable properties.
6. Each command repetition receives fresh candidate state. Recheck all locked
   source/evaluator content after execution, including the candidate itself.
7. Return stable evidence with `accepted`, `outcome`, `failure`, gate receipts,
   snapshot/contract/artifact digests and an `evidence_digest`.
8. In the benchmark only, score the selected immutable artifact once in a new
   workspace. Record `accepted` and `heldout_pass` separately. No scoring result
   goes back into candidate generation.

Stable verdict names are `accepted_under_declared_checks`,
`rejected_with_counterexample`, `inconclusive`, `environment_failure` and
`budget_exhausted`. Legacy CLI task statuses remain `COMPLETED`/`FAILED` for
compatibility; the structured `outcome` supplies the distinction.

Objects live in the ignored `.cdavc/artifacts/<sha256>.json` directory. Digests
detect content changes; they are not signatures or independent attestations.
Runtime receipts may contain private project source: do not commit or publish
the artifact directory indiscriminately.

## Accounting and budgets

`--max-calls`, `--max-tokens` and `--max-wall-seconds` are per task (CLI) or per
task/arm (benchmark). JSON re-asks and context retrieval consume the same call
and token budget as ordinary generation. A missing input or output count makes
the corresponding total unknown; `known_token_in`/`known_token_out` are only
lower bounds. `call_log`, `usage_complete` and `unmetered_calls` remain visible.

Under an explicit token cap, unmetered work is inconclusive rather than free.
Reasoning/cache counters, when supplied, are preserved as details of the
provider totals, not added a second time. No character-to-token estimate is
presented as measured usage.

Limits are checked between operations and after requests/checks. They do not
interrupt an in-flight model request or subprocess; one operation can overrun
its cap and is then rejected. Test subprocesses also have their own timeout.
Benchmark wall caps include final evaluation; a final-stage overrun never
re-enters generation. A previously selected artifact can therefore have
`accepted=true` while the overall run is `budget_exhausted` and `pass=false`.

Old/changed experiment fingerprints cannot resume together. Start a new JSONL
for a new protocol/configuration; historical reports remain historical evidence.

## Context and edits

`--context-budget N` is a **source-context character budget**, not a token cap
or a bound on the entire prompt. The task contract and bounded repair feedback
also consume input tokens. Add public caller/dependency files with repeatable
`--context-file PATH` or task-graph `context_files`.

Models can return either of these instead of a candidate:

```json
{"context_search": "symbol or words"}
```

```json
{"context_requests": ["chunk_id_from_the_catalogue"]}
```

The controller responds with bounded exact source, then requests the candidate
again. These are counted provider calls, not extra candidate draws. The default
limit is two retrieval requests per draw; use `--max-context-requests` to change
it. Benchmark context includes implementation source and explicitly published
`context_files`, not the hidden evaluator merely because it is hash-locked.

Edits match the original file exactly once. Several edits to the same file must
be disjoint in original coordinates; they cannot depend on earlier replacement
text. Optional edit `base_sha256` guards the original bytes. Mixing a whole-file
replacement and edits for the same target is rejected. Filesystem-error rollback
is best-effort if the filesystem also refuses restoration; this is not a
crash-atomic multi-file filesystem transaction.

## Executable properties and flake triage

Task graphs, benchmark tasks and standalone contracts accept `properties`:

```json
{
  "name": "negative input is rejected",
  "file": "src/answer.py",
  "symbol": "answer",
  "args": [-1],
  "raises": "ValueError"
}
```

Use exactly one of `raises` (a built-in exception name) or `expected` (a finite
JSON value). Optional `kwargs` supplies keyword arguments; `unchanged_args: true`
also checks that inputs were not mutated. Properties invoke actual candidate
code in fresh Python interpreters. An unrelated or unreachable `raise` does not
prove the runtime property. For `cdavc run`, pass a JSON case array with
`--property-file FILE`; contracts can also set `check_repeats` (1–5), exposed as
`--check-repeats` by `run`.

Conflicting repeated verdicts are inconclusive. Consistent failed checks remain
failures; there is no “retry until green” flake waiver. Import/start/timeout
problems are distinct from property counterexamples. The legacy AST guard is
still coarse, and finite properties are not exhaustive correctness proofs.

Run the frozen, no-model diagnostic:

```bash
PYTHONPATH=src python3 -m cdavc audit-fixtures \
  --fixtures benchmarks/verifier_fixtures.json \
  --output results/verifier-diagnostic-v1.json
```

The measured constructed fixture set has six incorrect and four correct
artifacts. Public/AST-only checks accepted all six incorrect artifacts;
adding declared properties accepted none of them. Both modes rejected zero of
the four correct artifacts. The JSON/Markdown reports include fixture and
evidence digests and explicitly limit that result to these authored cases.
It is not a model accuracy, generalization or statistical superiority estimate.

## Exported Claude/Codex/local outputs

The adapters consume **exports**, not vendor SDKs, credentials, saved sessions or
undocumented vendor response formats. `--source` is a user-supplied provenance
label; it never changes the verifier. Accepted transport formats are the same
`files`/`edits` JSON used by the runner and a strict textual unified-diff subset.

From this repository root, exercise a frozen diff without changing its project:

```bash
PYTHONPATH=src python3 -m cdavc verify \
  --directory examples/external \
  --contract examples/external/contract.json \
  --candidate examples/external/candidate.diff --format diff --source codex \
  --output results/external-verify-demo.json
```

`examples/external/contract.json` is the standalone contract schema. `verify`
writes evidence but **never publishes the patch or asks a model**. Diff parsing
uses exact original line coordinates/context; it never fuzzily applies hunks.
Renames, deletions, binary/mode changes, quoted Git paths and prose wrappers are
explicitly unsupported. New textual files are supported through `/dev/null`.

An optional `--telemetry FILE` uses this vendor-neutral schema:

```json
{
  "complete": true,
  "calls": [
    {"purpose": "generation", "prompt_tokens": 100, "completion_tokens": 30}
  ],
  "wall_time_seconds": 1.5,
  "limitations": ["Counters are exported by the producing agent."]
}
```

Include **every** upstream generation, retry, re-ask, summary, tool-model and
judge call. Missing usage or an incomplete call inventory stays unknown, never
zero. Supplied cache/reasoning usage can accompany calls in `usage`. A claimed
complete export is still self-reported, not independently vendor-attested.

A comparison manifest specifies one project directory, contract, shared
generation budget and a list of named exports. See
`examples/external/comparison.json`:

```bash
PYTHONPATH=src python3 -m cdavc compare \
  --manifest examples/external/comparison.json \
  --output results/external-comparison-demo.json
```

**The checked-in usage sidecar is explicitly synthetic demonstration data.**
It is not a Claude/Codex/local inference measurement. Replace the exports and
sidecars with actual observations before doing a real comparison.

`matched_reported_budget` requires identical experiment fingerprints,
complete reported usage and reported compliance with explicit common caps.
Different actual spend under the same caps is allowed. Missing/incomplete usage
or exceeded/unverifiable caps makes the comparison inconclusive (exit 1), not a
token-saving claim. Malformed or incompatible records fail with exit 2.
Individual artifact correctness evidence remains visible independently of cost.

## Verification and limits

```bash
python3 -m pip install '.[test]'
python3 -m pytest -q
make test PYTHON=python3
make benchmark-mock PYTHON=python3
```

The package still has no runtime dependencies. Pytest is an optional test tool;
the unittest path remains stdlib-only. The mock benchmark checks plumbing and
the frozen corpus, not model quality, and reports unavailable usage honestly.

Fresh copies, evaluator hashes and content-addressed artifacts are **not an OS
sandbox**. Processes retain user permissions, environment and network access;
hostile code can escape those boundaries or attack the harness. Use trusted
projects/evaluators/candidates or provide an independent OS/container isolation
boundary. Python/property checks require available local runtimes/dependencies;
the harness does not silently install project dependencies or vendor agents.

No paid or live vendor comparison is implied by the fixture/example reports.
Real matched-generation experiments and broader correct-rejection/flake studies
remain necessary before making model-quality or token-efficiency claims.
