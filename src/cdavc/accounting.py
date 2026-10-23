"""Per-request receipts and bounded generation, without estimated token claims."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from .providers import ProviderCompletion


class BudgetExceeded(ValueError):
    def __init__(self, message: str, *, outcome: str = "budget_exhausted") -> None:
        super().__init__(message)
        self.outcome = outcome


@dataclass(frozen=True)
class Budget:
    max_calls: int | None = None
    max_tokens: int | None = None
    max_wall_seconds: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_calls", "max_tokens"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise ValueError(f"{name} must be a positive integer")
        value = self.max_wall_seconds
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or value <= 0):
            raise ValueError("max_wall_seconds must be finite and positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


class UsageLedger:
    def __init__(self, budget: Budget | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.budget = budget or Budget()
        self.clock = clock
        self.started = clock()
        self.entries: list[dict[str, Any]] = []

    def check(self, *, before_call: bool = False) -> None:
        if self.budget.max_wall_seconds is not None and self.clock() - self.started >= self.budget.max_wall_seconds:
            raise BudgetExceeded("wall-clock budget exhausted")
        if before_call and self.budget.max_calls is not None and len(self.entries) >= self.budget.max_calls:
            raise BudgetExceeded("provider call budget exhausted")
        if self.budget.max_tokens is not None and self.entries:
            total = self.summary()["total_tokens"]
            if total is None:
                raise BudgetExceeded("token budget cannot be verified: unmetered call", outcome="inconclusive")
            if total > self.budget.max_tokens or (before_call and total >= self.budget.max_tokens):
                raise BudgetExceeded("token budget exhausted")

    def record(self, completion: ProviderCompletion | None, *, purpose: str, request_digest: str,
               elapsed: float, error: Exception | None = None) -> None:
        metadata = completion.metadata if completion is not None else {}
        usage = metadata.get("usage", {}) if isinstance(metadata, Mapping) else {}
        usage = usage if isinstance(usage, Mapping) else {}
        prompt_details = usage.get("prompt_tokens_details", {})
        output_details = usage.get("completion_tokens_details", {})
        finish_reason = metadata.get("finish_reason") if isinstance(metadata, Mapping) else None
        self.entries.append({
            "call": len(self.entries) + 1,
            "purpose": purpose,
            "status": "error" if error is not None else "completed",
            "error_type": type(error).__name__ if error is not None else None,
            "finish_reason": finish_reason if isinstance(finish_reason, str) else None,
            "request_digest": request_digest,
            "response_digest": hashlib.sha256(completion.text.encode()).hexdigest() if completion else None,
            "model": completion.model if completion else None,
            "prompt_tokens": _count(completion.prompt_tokens) if completion else None,
            "completion_tokens": _count(completion.completion_tokens) if completion else None,
            "cached_input_tokens": _count(prompt_details.get("cached_tokens")) if isinstance(prompt_details, Mapping) else None,
            "cache_creation_input_tokens": _count(usage.get("cache_creation_input_tokens")),
            "reasoning_tokens": _count(output_details.get("reasoning_tokens")) if isinstance(output_details, Mapping) else None,
            "wall_time_seconds": max(0.0, elapsed),
        })

    def summary(self) -> dict[str, Any]:
        inputs = [entry["prompt_tokens"] for entry in self.entries]
        outputs = [entry["completion_tokens"] for entry in self.entries]
        known_in = sum(value for value in inputs if value is not None)
        known_out = sum(value for value in outputs if value is not None)
        complete_in = bool(inputs) and all(value is not None for value in inputs)
        complete_out = bool(outputs) and all(value is not None for value in outputs)
        complete = complete_in and complete_out
        any_known = any(value is not None for value in inputs + outputs)
        return {
            "calls": len(self.entries), "usage_complete": complete,
            "unmetered_calls": sum(entry["prompt_tokens"] is None or entry["completion_tokens"] is None
                                   for entry in self.entries),
            "token_usage_source": "provider" if complete else "provider_partial" if any_known else "unavailable",
            "token_in": known_in if complete_in else None, "token_out": known_out if complete_out else None,
            "known_token_in": known_in, "known_token_out": known_out,
            "total_tokens": known_in + known_out if complete else None,
            "budget": self.budget.to_dict(),
        }


def normalise_completion(value: Any) -> ProviderCompletion:
    if isinstance(value, ProviderCompletion):
        return value
    if isinstance(value, str):
        return ProviderCompletion(value)
    if isinstance(value, Mapping):
        text = value.get("text", value.get("content"))
        usage = value.get("usage", value)
        model = value.get("model")
    else:
        text = getattr(value, "text", getattr(value, "content", None))
        usage = getattr(value, "usage", getattr(value, "__dict__", {}))
        model = getattr(value, "model", None)
    if not isinstance(text, str):
        raise ValueError("provider completion has no text")
    usage = usage if isinstance(usage, Mapping) else {}

    def first(*names: str) -> int | None:
        return next((_count(usage[name]) for name in names if _count(usage.get(name)) is not None), None)

    return ProviderCompletion(text, first("prompt_tokens", "input_tokens", "token_in"),
                              first("completion_tokens", "output_tokens", "token_out"),
                              model if isinstance(model, str) else None, {"usage": dict(usage)})


def complete_recorded(provider: Any, messages: Sequence[Mapping[str, Any]], ledger: UsageLedger,
                      *, purpose: str = "generation", seed: int | None = None) -> ProviderCompletion:
    """Record successes AND failures; budget rejection before dispatch is not a call.

    Token and wall caps are checked before and after requests. They do not make
    providers interruptible: one response may overrun a cap and is then rejected.
    Missing token counters under a token cap yield inconclusive, never free work.
    """
    ledger.check(before_call=True)
    request_digest = digest({"messages": list(messages), "seed": seed})
    started = ledger.clock()
    try:
        method = (getattr(provider, "complete_with_metadata", None)
                  or getattr(provider, "complete_with_usage", None) or provider.complete)
        try:
            parameters = inspect.signature(method).parameters
        except (TypeError, ValueError):
            parameters = {}
        supports_seed = "seed" in parameters or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())
        value = method(messages, seed=seed) if seed is not None and supports_seed else method(messages)
        completion = normalise_completion(value)
    except Exception as exc:
        ledger.record(None, purpose=purpose, request_digest=request_digest,
                      elapsed=ledger.clock() - started, error=exc)
        raise
    ledger.record(completion, purpose=purpose, request_digest=request_digest, elapsed=ledger.clock() - started)
    ledger.check()
    return completion
