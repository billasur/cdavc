# Self-improving CD-AVC via a pi extension

Status: PROTOTYPE, offline-verified, including a real load of the extension in
pi 1.4.0 (npm `@earendil-works/pi-coding-agent`). No live token-spending run
has been executed; no measured improvement exists yet.

## Idea

The CD-AVC harness improves itself: propose a change, evaluate on a fixed
benchmark, keep only if it measurably helps at no greater compute cost,
otherwise roll back. The evaluator is outside the improving agent's editable
scope.

## Pieces

- `self_improve/config.py` - the ONLY candidate-editable surface: `retry_cap`
  (0..3), `prompt_layout` (default|stable-prefix), `lenient_parse` (bool),
  each mapping to an existing BenchmarkRunner argument. Validation rejects
  unknown keys, so the surface cannot widen itself.
- `self_improve/manifest.py` + `self_improve/protected/MANIFEST.sha256` -
  pinned SHA-256 hashes over the whole loop code, the scorer (src/cdavc),
  the protected task list, benchmarks_dev2 and benchmarks_heldout (296
  files). The controller verifies the tree before AND after every
  evaluation.
- `self_improve/proposer.py` - ScriptedProposer (deterministic one-knob
  walk) and ModelProposer (asks a model for the next config, grounded in
  measured history; output is parsed through HarnessConfig validation so the
  model cannot leave the surface; refuses to construct without
  spend_approved=True; one re-ask on invalid replies; `null` stops the loop).
- `self_improve/evaluator.py` - SimulatedEvaluator (mechanics tests only,
  NOT a measurement) and LiveEvaluator (real BenchmarkRunner, MEASURED,
  requires a token cap).
- `self_improve/controller.py` - the loop. Keep rule is equal-cost: more
  passes only count at no-greater total tokens, equal passes only at strictly
  fewer tokens. A config that passes more only because it retried more is
  NOT kept. A single-seed keep is logged "measured (single-seed,
  provisional)"; with `--validate` the candidate is re-run against the
  incumbent on seeds 2 and 3 and only kept if it wins the equal-cost
  comparison on every validation seed - otherwise it is rolled back as
  single-seed noise. Such a keep is logged "multi-seed observed gain under
  this protocol" with its caveats: small N, selected on the dev2 set, NOT a
  validated research result. Validation re-runs spend tokens too.
- `self_improve/budget.py` - one cumulative token budget per run covering
  EVERYTHING: model-proposer calls, seed-1 evaluations and validation
  re-runs. Two guards: (1) no new evaluation/proposal starts past 80% of the
  cap; (2) BudgetedProvider wraps every request, sends max_tokens
  (--max-output-tokens, default 4096), and REFUSES a request whose estimated
  prompt tokens + max_tokens would cross the cap. Calls are sequential, so at
  most one request is in flight. Hard-cap honesty: the prompt estimate
  assumes >= 3 chars per BPE token (English/code averages ~4, so this
  overestimates); the cap is hard only while that bound holds - a pathological
  tokenizer ratio could overshoot by the prompt-side difference on one
  in-flight request. This is a bounded budget with a stated assumption, not
  an absolute guarantee. Providers reporting no usage are charged the worst
  case. BudgetExhausted aborts the benchmark run (it subclasses
  BenchmarkError; benchmark.py now re-raises those instead of recording them
  as candidate failures).
- `pi_extension/cdavc/index.ts` - the pi extension: `cdavc_verify` tool
  (public gates only; hidden tests never run through it), a write/edit/bash
  guard over protected paths, and `/cdavc-improve` (simulated mode only;
  live runs are CLI-only and need `--approve-spend --token-cap N`).

## Protection: what it is and what it is not

The manifest check catches protected-file changes however they are made -
write/edit tools, bash redirection, `git commit`/`git reset` (it pins content,
not git HEAD), symlink replacement, and edits to the controller itself.
Bypass tests: tests/test_self_improve.py (`test_bypass_*`).

It is a GUARD RAIL, not a security boundary. An agent with unrestricted shell
access in this repo could rewrite both the protected files AND the manifest
(`test_manifest_rewrite_is_the_documented_limit` pins this). Real isolation
needs enforcement outside the repo: read-only mount, separate OS user, or
CI-side evaluation. Until that exists, DO NOT run an unsupervised agent with
shell access against this loop, and treat manifest writes as a human-only
step (regenerate + review + commit). Do not describe the scorer as
"protected" without this caveat. The pi extension's tool guards are
additionally only string-matching and only apply inside pi.

## Verified offline (24 Oct)

- 28 tests in tests/test_self_improve.py pass, including: a full real
  BenchmarkRunner run of one dev2 task through the cdavc arm (git worktree,
  AST gate, public/hidden/regression tests) with a mock provider; manifest
  bypass tests; equal-cost keep rule; provisional vs validated keep;
  ModelProposer surface confinement with a mock provider.
- Full suite: 123 passed, 1 pre-existing environmental failure
  (test_launch memory detection; fails identically on clean night-run-v2).
- Extension loaded in real pi 1.4.0: `cdavc_verify` appears in the live
  session's tool list. Tool, guard and `/cdavc-improve` handler all exercised
  through pi's jiti loader: PASS/FAIL/refusal cases, write/edit/bash blocks,
  and a simulated 2-iteration loop run through the command handler.
  No model was configured in the sandbox (pi defaulted to a denied bedrock
  endpoint), so no model-driven pi session was run.

## Not done / open gaps

- Live measured run: needs a model key and a token-cap approval, and must
  pass --proposer explicitly: `model` for the user's model-driven
  improvement, or `scripted` for a deliberate mechanical smoke (labelled as
  such - a scripted live run is not model-driven improvement). The Groq
  gpt-oss-20b free-tier TPD cap was hit during the 20 Oct runs (per run
  records); whether quota is available now is unverified - check live before
  assuming either way. `scripts/self_improve_quota_probe.py` does that check
  with one max_tokens=1 call (a few tokens, run only after approval) and
  prints the rate-limit headers. `--base-url` and `--model` allow any
  OpenAI-compatible endpoint the user selects. `--token-cap` is the TOTAL
  budget: proposals, evaluations and validation re-runs all count.
- Objective is dev2 pass count, cdavc arm, seed 1 (+ seeds 2,3 with
  --validate). dev2 is a dev set; held-out stays frozen and unrun.
- Widening the editable surface beyond the three knobs (feedback templates,
  parser code) is a human decision; each new surface needs the loop code and
  manifest regenerated by a human (write_manifest + commit).
