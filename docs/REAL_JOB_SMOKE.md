# Real cached-model smoke run

## Date

2026-10-19

## Model

The cached `Qwen2.5-7B-Instruct-GGUF` split GGUF model was served through the
installed `llama-server` OpenAI-compatible endpoint. The model files remain in
the local Hugging Face cache and are not part of this repository.

## Job

CD-AVC was given a temporary trusted project containing:

- `src/answer.py` with an incorrect implementation;
- `tests/test_answer.py` requiring `answer(41) == 42`;
- one task graph task requiring the `answer` symbol;
- one retry allowance;
- the local OpenAI-compatible provider.

## Result

The actual cached local model produced a valid implementation response. CD-AVC
accepted it after the AST, targeted-test and regression gates:

```text
CLI_EXIT=0
project_id=qwen-cache-smoke
TASK-001: COMPLETED
attempts: 1
```

The resulting implementation was semantically correct:

```python
def answer(n):
    return n + 1
```

The task report and execution log were generated in the temporary project and
were discarded after the smoke run.

## Important boundary

This proves the provider/runtime/supervisor path on one small Python task. It
does not prove broad coding quality, production safety, benchmark improvement,
or Bonsai runtime compatibility.
