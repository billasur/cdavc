# CD-AVC

Contract-Driven Asymmetric Verification Cage: a deterministic harness for
testing patches produced by local coding models or exported by external agents.

## Current scope

The runner validates task graphs, transactionally applies allowed changes,
checks Python syntax/symbols and executable properties, and runs declared public
targeted/regression checks. Every candidate and check repetition starts from
fresh snapshot state. The scripted mock workflow runs without inference or keys.

The P0–P4 reliability implementation adds held-out scoring isolated from public
selection, per-call accounting and budgets, strict experiment fingerprints,
content-addressed evidence, retrievable budgeted context, flake triage and
model-independent export verification. Read
[`docs/VERIFICATION_ROADMAP.md`](docs/VERIFICATION_ROADMAP.md) for acceptance
tests, schemas, commands, measured fixture results and limitations.

v2 groundwork includes a standard-library OpenAI-compatible provider adapter.
It is suitable for a local instruct/coder endpoint, including a future Bonsai
2 2B/4B/9B/27B runtime. Model weights are never part of this repository.
The local Hugging Face cache is supported through the runtime discovery helpers;
the cache itself is never copied or committed.

**Trust boundary:** v0 is for trusted local repositories, task graphs and model
endpoints. Declared test commands execute as the current user with its network,
environment and filesystem permissions. The temporary workspace protects the
active source tree from failed candidates; it is not a security sandbox.

## Requirements

- Python 3.11 or 3.12 (the Docker path pins Python 3.11)
- Git for the test fixtures; Docker is optional for clean-Linux testing
- No network access or API key is required for v1

## Install

For a local checkout with Python 3.11 or 3.12:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --no-deps .
.venv/bin/cdavc --help
```

The package has no runtime dependencies. The build backend may need access to
the pinned setuptools build dependency when building from a completely empty
environment; the offline judge path uses the Docker image and does not install
third-party runtime packages.

The pinned build dependency is listed in `requirements.lock`:

```bash
.venv/bin/python -m pip install -r requirements.lock
```

For the complete first-run flow, read [`docs/ONBOARDING.md`](docs/ONBOARDING.md).
It covers the mock activation path, task graphs, local endpoints, optimized
llama/MLX launch, Bonsai compatibility, reports, recovery and clean-Linux
verification.

The high-level architecture is shown in
[`docs/cdavc-system-design.svg`](docs/cdavc-system-design.svg), with an
explanation in [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md). A real cached
Qwen local-model smoke run is recorded in
[`docs/REAL_JOB_SMOKE.md`](docs/REAL_JOB_SMOKE.md).

## Use it on your own project

`cdavc run` takes one sentence, the file the model may change, and the test that
defines done:

```bash
cdavc run "add a discount_rate argument to total() applied before tax" \
    --file src/shop/pricing.py \
    --test tests/test_pricing.py \
    --regression "python -m pytest -q" \
    --endpoint http://127.0.0.1:8080/v1/chat/completions --model local-model
```

- `--file` (repeatable) is the only file the model may change. Any other file in
  its answer is rejected before anything is written.
- `--test` (repeatable) must already exist, and the suite it names must run at
  least one test. cdavc does not write the test for you: the test is the
  definition of done, so you write it first.
- `--regression` runs the project's own suite after the targeted test. Without
  it, `python -m unittest discover -s tests` is used when `tests/` exists.
- `--test-command` overrides the targeted command when your tests are not where
  unittest discovery looks, for example `--test-command "npm test"`. A command
  that runs no tests is rejected rather than counted as a pass.
- `--dry-run` verifies the change and prints the diff while leaving the project
  untouched. Without it the change is copied into the project only after every
  gate passed.
- `--samples N` spends at least N candidate draws before giving up, each one
  told why the draw before it was rejected. `--max-retries` still sets the floor,
  so `--samples 4` with the default two retries means four draws, not six.
- `--directory DIR` points at the project when you do not run from its root;
  `--file` and `--test` are always relative to it.
- `--invariant` (repeatable) adds a contract sentence the change must satisfy;
  `--symbol` (repeatable) requires a name to exist afterwards, which is checked
  for Python files.
- `--provider mock --mock-response answer.json` replays a scripted
  `{"files": {...}}` or `{"edits": [...]}` answer with no endpoint, which is how
  the flow above can be exercised offline.
- `--max-calls`, `--max-tokens` and `--max-wall-seconds` bound per-task work.
  Retrieval and re-asks consume call/token budgets. Unknown usage remains
  incomplete; under a token cap it makes the result inconclusive.
- `--context-budget` bounds source-context characters, not estimated tokens.
  `--context-file` publishes additional caller/dependency source; omitted chunks
  remain searchable/retrievable through counted requests.
- `--property-file` supplies executable value/exception/non-mutation cases.
  `--check-repeats 2` uses fresh repetitions; conflicting verdicts are
  inconclusive rather than retried until green.
- A reply that is nearly that shape is repaired rather than thrown away: a
  Markdown fence, raw newlines in a string, an unescaped `"` inside the code the
  model wrote, a triple-quoted value, or prose before/after the object. A local
  model that writes `raise ValueError("empty")` into a JSON string is applied
  instead of rejected. A reply with no recoverable object still is not.
- `--temperature`, `--top-p`, `--top-k` and `--max-output-tokens` set the
  sampling controls your model card documents (local servers accept `top_k` in
  the request body). A reply truncated at the token limit is rejected with that
  reason instead of failing JSON parsing.
- A rejected draw is routed by failure class: syntax/name/type errors quote the
  rejected candidate for repair, while assertion failures get the failure text
  and a fresh derivation. A reply repeating an earlier rejected reply
  byte-for-byte stops the run with a `stagnation` outcome instead of spending
  the remaining draws, and a candidate byte-identical to the original is
  rejected when the declared checks would accept the unchanged project: those
  checks do not discriminate the task.

A run writes `execution_log.json`, `execution_report.md` and, when something
changed, `execution_patch.diff` to the project root. The exit status is `0` when
the change was verified, `1` when every candidate was rejected, and `2` for a
usage or provider error. A model server that cannot answer stops the run after the
first request instead of spending the repair attempts: an unreachable server is
not a rejected candidate.

`cdavc verify` evaluates exported JSON, edits or a strict unified diff without
calling a model or publishing the patch. `cdavc compare` applies one frozen
snapshot/contract and common declared caps to labelled exports. Claude, Codex
and local are provenance labels, not alternative verification paths or live
vendor integrations. Missing upstream telemetry prevents a matched-cost claim.
See the runnable, explicitly synthetic `examples/external/` workflow in the
[verification guide](docs/VERIFICATION_ROADMAP.md#exported-claudecodexlocal-outputs).

The same `cdavc verify` powers a deterministic pre-merge GitHub gate:
`.github/workflows/cdavc-gate.yml` replays a pull request's implementation diff
through the contract with the verifier installed from the reviewed base branch
and the test files hash-locked to it, so a PR cannot weaken its own judge or
grade itself on edited tests. [`docs/PRE_MERGE_GATE.md`](docs/PRE_MERGE_GATE.md)
documents the contract and its honest limits; the October 2026 competitive and
research review behind this direction is [`docs/RESEARCH-2026-10.md`](docs/RESEARCH-2026-10.md).

## Showcase site

The scroll-controlled 3-D live demo lives in `showcase/`. It pins one
full-viewport task-patch scene and uses scroll as the timeline: contract,
bounded local model patch, locked-test hash, AST contract, isolated worktree,
regression and verified merge. Three.js, GSAP/ScrollTrigger and Lenis are
vendored under `showcase/vendor/`; the page has no CDN fonts or runtime fetches.
Preview it locally with:

```bash
python3 -m http.server 4173 --directory showcase
```

Deploy it from the repository root with the Vercel CLI:

```bash
vercel deploy --cwd showcase
```

The showcase uses measured smoke evidence from the repository and does not
claim a benchmark improvement. The local model and verification process remain
local; Vercel hosts only the explanatory visual demo.

Verify the checked-in browser libraries offline with:

```bash
cd showcase
npm run verify-vendor --offline
```

## Run tests

```bash
make test
```

The test command uses only Python's standard library and is therefore suitable
for offline execution.

Alternatively, install the optional test tool and run the same project tests:

```bash
python3 -m pip install '.[test]'
python3 -m pytest -q
```

For an optional coverage report, install the development-only tool into the
project virtual environment and run:

```bash
.venv/bin/python -m pip install coverage
make coverage PYTHON=.venv/bin/python
```

Use the coverage command to measure the current tree; no historical coverage
percentage is claimed for newly added code.

## How to reproduce the benchmark

The benchmark is local-only and resumable. It evaluates the same fixed set of
50 original HumanEval/MBPP-style Python tasks in five arms:

- `baseline_single`: one candidate draw selected using public checks;
- `baseline_retry`: the same plain baseline with bounded retries, where a retry
  receives the previous failing **public** output and the candidate that produced
  it, so it can repair rather than re-derive from scratch;
- `cdavc`: the same local model behind locked evaluator hashes, an AST contract
  check, fresh snapshot copies, public tests, the regression
  gate and bounded retries;
- `cdavc_sampled`: the `cdavc` cage with a best-of-N draw budget (`--samples`),
  which keeps the first candidate that clears the public gate; and
  `cdavc_sampled_repair`, the same draw budget but with each draw told why the
  previous public gate failed, which separates the budget effect from the
  feedback effect.

Every arm's selected artifact is scored once by the common final evaluator,
including the held-out tests. Hidden results never select a draw or enter
repair prompts. Records distinguish `accepted` from `heldout_pass`. Different
draw limits are not matched-token evidence; incomplete costs stay unknown.

The task source and evaluator boundary are documented in
[`benchmarks/README.md`](benchmarks/README.md). The hidden evaluator is never
included in the initial prompt. Do not modify the corpus after inspecting
results; create a new corpus version for a new experiment.

### CI/offline smoke run

This performs a bounded offline plumbing check and does not contact a model server:

```bash
make benchmark-mock PYTHON=.venv/bin/python
```

It appends one JSON object per completed task/arm to
`results/benchmark-v5-mock.jsonl` and writes `results/REPORT-v5-mock.md`. If interrupted, run
the same command again; completed `task_id`/`arm` pairs are skipped. The mock
provider reports token counts as unavailable rather than estimating them.

### Long local-model run

Start a local OpenAI-compatible server separately (for example, llama.cpp or
MLX bound to `127.0.0.1`). The benchmark rejects non-local endpoints and never
uses cloud inference. From the repository root, run:

```bash
PYTHONPATH=src .venv/bin/python -m cdavc.benchmark . \
  --tasks benchmarks/tasks.json \
  --records results/benchmark-v5-local.jsonl --report results/REPORT-v5-local.md \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model 'your-local-model-name' \
  --quantisation 'Q4_K_M' \
  --version 'your-model-version-or-checksum' \
  --hardware 'Apple M3 MacBook Air 16 GB' \
  --seed 20261019 \
  --timeout 300 \
  --retry-cap 3
```

Leave that process running overnight if needed. Each task/arm record is flushed
and fsynced to the specified records file before the next arm starts, so a
crash or interruption loses at most the in-progress task/arm. Re-run the same
command to resume. The report is regenerated from the JSONL at
the specified report path and contains only measured values, including paired
pass-rate differences with a 95% confidence interval, measured time/token
overhead, and cage-hurt cases. A missing provider token count or memory value
is shown as unavailable; no value is estimated.

Source, evaluator, engine, task or budget changes invalidate the fingerprint;
use a new JSONL rather than mixing incompatible or legacy runs. Planned records
and report paths are excluded from the snapshot so an identical command can
resume after producing its own report.

The harness records the selected model, quantisation, version, hardware string,
seed, provider-reported token usage, harness peak memory measurement and its
measurement source on every row. On macOS, peak memory is the benchmark
harness process's `resource.getrusage` high-water mark; the source is explicit
in each JSONL record because a separately managed model server is not folded
into that number.

## Run the deterministic demo

```bash
make run-demo
```

The first mock response is intentionally rejected by the test suite. The
second response passes and the demo writes its execution report beside the
task graph.

## Rebuild and test in clean Linux Docker

```bash
docker build --tag cdavc:test .
docker run --rm --network none cdavc:test
```

Or use:

```bash
make docker-test
```

The Docker command runs the same offline test suite with networking disabled.

## Clean Linux command sequence

From a fresh checkout on a Linux machine with Python 3.11+:

```bash
git clone git@github.com:billasur/cdavc.git
cd cdavc
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps .
make test PYTHON=.venv/bin/python
make run-demo PYTHON=.venv/bin/python
```

The Docker-only clean rebuild is:

```bash
docker build --tag cdavc:test .
docker run --rm --network none cdavc:test
```

## Optional local model endpoint

The adapter accepts an OpenAI-compatible chat-completions endpoint:

```bash
cdavc path/to/task_graph.json \
  --provider openai \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model local-model
```

Set `CDAVC_API_KEY` only when the endpoint requires it. Use `.env.example` as
the configuration reference. A local model server and its weights are an
optional development dependency, not part of the reproducible Docker build.

For Bonsai GGUF files, use the PrismML llama.cpp fork. The stock Homebrew
`llama-server` currently rejects the cached Bonsai 2 9B MTP artifact because it
does not understand its custom GGML tensor type. See `docs/V2.md` for the
measured compatibility result and fallback guidance.

## Hardware-aware local launch

The next v2 slice applies the practical parts of Magnitude's approach without
copying its engine: conservative memory budgeting, quantized KV cache, bounded
prefill, limited concurrency, continuous batching, MTP flags for MTP artifacts,
and separate MLX cache/prefill controls.

Print the selected command before launching it:

```bash
cdavc-launch \
  --backend llama \
  --model /absolute/path/to/model.gguf \
  --memory-bytes $((16 * 1024 * 1024 * 1024))
```

Use `--run` only after checking the printed command. For Bonsai, pass the
PrismML-compatible server executable with `--executable`; the default
Homebrew/stock llama.cpp binary is not compatible with the cached custom Bonsai
formats.

## Deliberate limitations

This version does not claim to provide a security sandbox, generic memory-leak
detection, mutation testing, cloud quota routing, TypeScript support or a
benchmark improvement. Those require separate measurements and a larger scope.
