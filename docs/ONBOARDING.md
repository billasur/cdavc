# CD-AVC v0 onboarding

This guide takes a new user from an empty checkout to a verified local-model
run. Follow the steps in order the first time. Later runs can begin at Step 5.

## The first-session goal

The activation moment is:

> A user sees CD-AVC reject a bad implementation, retry with failure feedback,
> accept the corrected implementation, and produce a report.

Do not begin with Bonsai, cloud credentials or a large repository. First prove
the deterministic mock workflow. It is the fastest way to distinguish a CD-AVC
configuration problem from a model-runtime problem.

## Before you begin

You need:

- macOS Apple Silicon or Linux;
- Python 3.11 or 3.12;
- Git;
- a checkout of this repository;
- Docker only for the optional clean-Linux verification path.

CD-AVC v0 is a trusted-input tool. Do not run a task graph, repository or test
command supplied by an untrusted person. Declared commands execute with the
current user's permissions. Read `SECURITY.md` before using the tool on real
projects.

## Step 1 — Get the source

```bash
git clone git@github.com:billasur/cdavc.git
cd cdavc
```

If you received a source archive instead, enter the extracted `cdavc` folder.
Confirm that the project root contains `README.md`, `pyproject.toml`,
`Dockerfile` and `Makefile`:

```bash
ls README.md pyproject.toml Dockerfile Makefile
```

## Step 2 — Select the supported Python runtime

Check the interpreter before creating an environment:

```bash
python3 --version
```

You need Python 3.11 or newer, and below 3.13 for the published package.
If `python3` points to an older system Python, use an explicit interpreter:

```bash
python3.11 --version
```

The repository records the intended version in `.python-version`.

## Step 3 — Create the project environment

Create the environment inside the project. It is ignored by Git and does not
modify the global Python installation:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --no-deps .
```

Verify the installed commands:

```bash
.venv/bin/cdavc --help
.venv/bin/cdavc-launch --help
```

If installation fails because the build backend cannot be downloaded, connect
temporarily to the package index or use the Docker/CI path with its build
dependencies available. CD-AVC itself has no runtime Python dependencies.

## Step 4 — Run the built-in checks

Run the standard test suite before using a model:

```bash
make test PYTHON=.venv/bin/python
```

Expected result:

```text
Ran 49 tests
OK
```

If this fails, stop here. Do not troubleshoot llama.cpp or MLX yet. The core
harness must be green first.

## Step 5 — Run the first activation demo

The demo is deliberately deterministic. It starts with a bad candidate and
then supplies a corrected candidate:

```bash
make run-demo PYTHON=.venv/bin/python
```

Inspect the generated artifacts:

```bash
cat examples/demo/execution_log.json
cat examples/demo/execution_report.md
```

You should see:

1. `TASK-001` started;
2. attempt 1 rejected because the test failed;
3. attempt 2 accepted;
4. final status `COMPLETED`;
5. a report showing the failure and recovery.

This is the v0 activation moment.

## Step 6 — Understand the task graph

Copy `examples/demo/task_graph.json` into a project and edit it. Each task
should declare:

- a unique `id`;
- a human-readable `title`;
- `dependencies`;
- `implementation_files`;
- at least one existing `test_files` path;
- required Python `symbols`;
- optional invariants;
- a bounded `max_retries` value.

Use repository-relative paths only. Do not use absolute paths or `..` segments.

Example task shape:

```json
{
  "id": "TASK-001",
  "title": "Implement the parser",
  "dependencies": [],
  "implementation_files": ["src/parser.py"],
  "test_files": ["tests/test_parser.py"],
  "symbols": ["parse"],
  "invariants": ["empty input is rejected"],
  "test_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
  "max_retries": 2
}
```

The supervisor validates the graph before execution. A missing test file,
unknown dependency, duplicate ID, cycle or unsafe path is a configuration
failure, not a model failure.

## Step 7 — Run a trusted local project with the mock provider

The mock provider is the recommended first run for every new project:

```bash
.venv/bin/cdavc path/to/task_graph.json \
  --provider mock \
  --mock-response path/to/first-response.json \
  --mock-response path/to/repair-response.json
```

Each response must be JSON in this shape:

```json
{
  "files": {
    "src/parser.py": "complete file contents here\n"
  }
}
```

The provider may only change the implementation files declared by the task.
It must not change tests. Keep response files outside the repository if they
contain private source, or add only sanitized fixtures to Git.

## Step 8 — Connect a local instruct or coder model

Only do this after the mock run is green.

The local model must expose an OpenAI-compatible chat-completions endpoint. A
typical endpoint is:

```text
http://127.0.0.1:8080/v1/chat/completions
```

Run CD-AVC against it with:

```bash
.venv/bin/cdavc path/to/task_graph.json \
  --provider openai \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model your-local-model \
  --timeout 120
```

The endpoint must return a response shaped like:

```json
{
  "choices": [
    {
      "message": {
        "content": "{\"files\": {\"src/parser.py\": \"...\"}}"
      }
    }
  ]
}
```

Begin with a one-file task and a short implementation. Do not start with a
large multi-file task, a 27B model or a long context window.

## Step 9 — Prepare a local runtime conservatively

CD-AVC can print an optimized launch command without starting the process:

```bash
.venv/bin/cdavc-launch \
  --backend llama \
  --model /absolute/path/to/model.gguf \
  --memory-bytes $((16 * 1024 * 1024 * 1024))
```

Review the printed command before using `--run`. The policy may select:

- quantized q8 KV cache;
- a bounded context size;
- bounded prefill and batch sizes;
- limited concurrent sequences;
- continuous batching;
- MTP flags for an MTP artifact.

For an MLX model directory:

```bash
.venv/bin/cdavc-launch \
  --backend mlx \
  --model /absolute/path/to/mlx-model-directory \
  --memory-bytes $((16 * 1024 * 1024 * 1024))
```

These are conservative heuristics, not a replacement for a measured device
profile.

## Step 10 — Bonsai-specific setup

The cached Bonsai artifacts require runtime compatibility checks before use.
Read:

```text
docs/V2.md
docs/MAGNITUDE_RESEARCH.md
```

The stock Homebrew `llama-server` was observed to reject the cached Bonsai 2
9B custom GGUF with an invalid GGML tensor type. Use the PrismML-compatible
llama.cpp fork instead:

```bash
.venv/bin/cdavc-launch \
  --backend llama \
  --model /absolute/path/to/Ternary-Bonsai-2-9B-PQ2_0-MTP-Q8_0.gguf \
  --executable /absolute/path/to/prism-llama-server \
  --memory-bytes $((16 * 1024 * 1024 * 1024))
```

Do not report Bonsai as working until the server loads the model and responds
to a direct health or chat request.

## Step 11 — Verify the first real model response

Before running a full task graph, test the endpoint independently. The exact
request depends on the runtime, but the required behavior is:

1. server starts without model-load errors;
2. `/v1/chat/completions` accepts a small request;
3. the response contains assistant text;
4. a CD-AVC response can be parsed as the constrained `files` JSON object.

Then run one task with `max_retries: 0`. If the model emits malformed JSON,
keep the model/runtime configuration unchanged and first improve the prompt or
use a more code-oriented model.

## Step 12 — Read the execution report

Every run writes:

```text
execution_log.json
execution_report.md
```

Review these fields before trusting a result:

- task status;
- attempt count;
- rejected-candidate failure;
- targeted-test result;
- regression-test result;
- provider resolution;
- files changed.

`COMPLETED` means the declared deterministic gates passed. It does not mean
the implementation is secure, production-ready or semantically complete
beyond the declared tests.

## Step 13 — Clean Linux verification

When Docker is available:

```bash
make docker-test
```

This builds the project image and runs tests with networking disabled. The
image intentionally does not contain model weights or credentials.

If Docker is unavailable, run the equivalent local checks:

```bash
make test PYTHON=.venv/bin/python
make coverage PYTHON=.venv/bin/python
make package-test PYTHON=.venv/bin/python
```

Record Docker as unverified rather than treating these commands as an
equivalent Linux rebuild.

## Step 14 — Recovery guide

### `Python 3.11+` error

Select an explicit supported interpreter:

```bash
make test PYTHON=python3.11
```

### `declared test file does not exist`

Fix the task graph path. Test files must exist before the provider is called.

### `provider requires --endpoint`

Use `--provider mock` for offline onboarding, or supply a local OpenAI-compatible
endpoint for a real model.

### `provider request failed`

Check that the server is running, the endpoint path ends with
`/v1/chat/completions`, and the timeout is large enough for first-token latency.

### `invalid GGML tensor type`

The selected llama.cpp binary is not compatible with the model’s quantization.
Use the model’s documented runtime or switch to a compatible model artifact.

### Test failure after a candidate

Read the last failure in `execution_report.md`. Do not edit the locked tests to
make the candidate pass. Fix the implementation, task contract or model prompt.

## Step 15 — What to do after activation

Once the first task succeeds:

1. add a second independent task;
2. add a dependency between two small tasks;
3. run the mock provider again;
4. try a small instruct/coder model;
5. compare retry count and failure types;
6. only then try Bonsai 2 9B;
7. record memory, context, prefill and decode behavior;
8. keep the mock path as the reproducible regression test.

Do not use a benchmark score as the first activation metric. The first useful
metrics are:

- time to first successful verified task;
- percentage of candidates passing the targeted tests;
- retry count per task;
- malformed provider response rate;
- regression failures after task completion.

## Onboarding completion checklist

- [ ] Supported Python runtime selected.
- [ ] Project virtual environment created.
- [ ] Package installed locally.
- [ ] `cdavc --help` works.
- [ ] `make test` passes.
- [ ] Mock demo rejects and then repairs a candidate.
- [ ] Execution report inspected.
- [ ] Trusted-input boundary understood.
- [ ] Local endpoint tested independently, if used.
- [ ] Runtime command printed and reviewed before `--run`.
- [ ] Model compatibility verified, if using Bonsai.
- [ ] Docker test completed or explicitly recorded as unavailable.
