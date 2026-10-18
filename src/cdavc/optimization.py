"""Conservative local-runtime policy inspired by hardware-tuned engines.

This module chooses safe memory and concurrency defaults. It does not claim to
compile custom kernels or replace a real per-device benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareBudget:
    total_memory_bytes: int
    model_bytes: int
    reserve_bytes: int = 4 * 1024**3
    runtime_overhead_bytes: int = 1536 * 1024**2
    kv_bytes_per_token: int = 512 * 1024


@dataclass(frozen=True)
class RuntimeProfile:
    context_tokens: int
    kv_cache_type: str
    max_sequences: int
    prefill_tokens: int
    batch_tokens: int


def choose_runtime_profile(budget: HardwareBudget) -> RuntimeProfile:
    if min(
        budget.total_memory_bytes,
        budget.model_bytes,
        budget.reserve_bytes,
        budget.runtime_overhead_bytes,
        budget.kv_bytes_per_token,
    ) <= 0:
        raise ValueError("memory budget values must be positive")
    available = (
        budget.total_memory_bytes
        - budget.reserve_bytes
        - budget.runtime_overhead_bytes
        - budget.model_bytes
    )
    if available <= 0:
        raise ValueError("model and reserve exceed total memory")

    context = next(
        (candidate for candidate in (32768, 16384, 8192, 4096) if candidate * budget.kv_bytes_per_token <= available),
        2048,
    )
    max_sequences = 2 if budget.model_bytes <= 4 * 1024**3 and context >= 8192 else 1
    prefill_tokens = 512 if budget.model_bytes <= 4 * 1024**3 else 256
    return RuntimeProfile(
        context_tokens=context,
        kv_cache_type="q8_0",
        max_sequences=max_sequences,
        prefill_tokens=prefill_tokens,
        batch_tokens=min(1024, prefill_tokens * max_sequences),
    )
