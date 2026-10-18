# CD-AVC

Contract-Driven Asymmetric Verification Cage: a deterministic harness for
testing patches produced by small local coding models.

## Current scope

v1 runs entirely offline with a scripted mock provider. It validates a task
graph, applies only allowed implementation-file changes, checks Python syntax
and required symbols, runs targeted tests, runs regression tests, retries a
failed candidate, and writes `execution_log.json` plus `execution_report.md`.

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

- Python 3.11.x (pinned in `.python-version` and Dockerfile)
- Docker for the clean Linux test path
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

## Showcase site

The static motion/3-D pipeline showcase lives in `showcase/`. Preview it
locally with:

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

## Run tests

```bash
make test
```

The test command uses only Python's standard library and is therefore suitable
for offline execution.

For an optional coverage report, install the development-only tool into the
project virtual environment and run:

```bash
.venv/bin/python -m pip install coverage
make coverage PYTHON=.venv/bin/python
```

The current suite reports at least 96% line coverage. The remaining lines are
platform-specific memory detection and defensive subprocess/error branches.

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
