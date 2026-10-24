"""Cumulative token budget for a supervised self-improvement run.

One budget covers EVERYTHING the run spends: model-proposer calls, seed-1
evaluations, and multi-seed validation re-runs.

Two guards:
1. Evaluation-level soft start (80% of cap): no new evaluation/proposal
   starts past it - absorbs the gap between accounting points.
2. Request-level hard cap via BudgetedProvider: every request carries a
   max_tokens, and before launching, the wrapper refuses the request if
   estimated_prompt_tokens + max_tokens would cross the cap.

Prompt bounding: when tiktoken is available, prompt tokens are counted
EXACTLY for message contents with the model family's encoding (o200k for
gpt-oss), plus a per-message harmony framing allowance (16 tokens) and a
per-request provider-template allowance (1024 tokens) for framing the
provider adds server-side. Output and reasoning tokens are bounded by the
request's max_tokens (reasoning is billed as completion tokens by OpenAI-
compatible serving). Residual risk: provider-side template content beyond
the allowance on the single in-flight request (calls are sequential). When
tiktoken is unavailable, the chars/3 heuristic is used instead and the budget
is BEST-EFFORT - do not run under a promised hard cap in that mode.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from cdavc.benchmark import BenchmarkError as _Base
except Exception:  # pragma: no cover - src unavailable (unit isolation)
    _Base = RuntimeError


class BudgetExhausted(_Base):
    """Refuse to start/spend past the budget. Subclasses BenchmarkError so a
    benchmark run aborts instead of recording the refusal as task failures."""


# Fallback prompt-token estimate when tiktoken is unavailable: at least 3
# chars per token. Heuristic only - results are then labelled BEST-EFFORT.
CHARS_PER_TOKEN_ASSUMPTION = 3

# Per-message harmony framing allowance: <|start|> + role + <|message|> +
# content + <|end|> is about 4-6 tokens; 16 is conservative.
PER_MESSAGE_FRAMING = 16
# Per-request allowance for provider-side template content we cannot see
# (harmony system/developer preamble, tool preludes, assistant priming).
# Documented residual risk: if a provider injects more than this, a single
# in-flight request can overshoot the cap by the difference.
PROVIDER_FRAMING_ALLOWANCE = 1024


def estimate_prompt_tokens(text: str) -> int:
    return -(-len(text) // CHARS_PER_TOKEN_ASSUMPTION)  # ceil


def _o200k_encoding():
    try:
        import tiktoken
        return tiktoken.get_encoding("o200k_base")
    except Exception:
        return None


def count_prompt_tokens(messages, *, framing_allowance: int = PROVIDER_FRAMING_ALLOWANCE):
    """Exact o200k content tokens + documented framing allowances, or None
    when tiktoken is unavailable (caller falls back to the heuristic and must
    label the budget best-effort). Correct only for o200k-tokenizer models
    (the gpt-oss family); other models need their own encoding."""
    enc = _o200k_encoding()
    if enc is None:
        return None
    content = sum(len(enc.encode(str(m.get("content", "")))) for m in messages)
    framing = PER_MESSAGE_FRAMING * len(messages) + framing_allowance
    return content + framing


class Budget:
    def __init__(self, cap: int, *, soft_fraction: float = 0.8) -> None:
        if cap <= 0:
            raise ValueError("budget cap must be positive")
        self.cap = cap
        self.soft_limit = int(cap * soft_fraction)
        self.spent = 0

    def charge(self, tokens: int | None, what: str) -> None:
        if tokens:
            self.spent += tokens

    def check_can_start(self, what: str) -> None:
        if self.spent >= self.soft_limit:
            raise BudgetExhausted(
                f"budget soft limit reached ({self.spent}/{self.cap} tokens); "
                f"not starting {what}"
            )

    def check_request_fits(self, estimated_prompt: int, max_output: int, what: str) -> None:
        worst_case = estimated_prompt + max_output
        if self.spent + worst_case > self.cap:
            raise BudgetExhausted(
                f"refusing {what}: worst case {worst_case} tokens "
                f"(~{estimated_prompt} prompt + {max_output} max output) does not fit "
                f"the remaining budget ({self.cap - self.spent} of {self.cap})"
            )

    def summary(self) -> str:
        return f"{self.spent}/{self.cap} tokens spent (soft limit {self.soft_limit})"


class BudgetedProvider:
    """Provider wrapper enforcing a hard per-request budget check.

    Requires the wrapped provider to send a max_tokens (otherwise the output
    side is unbounded and no hard cap is possible - construction refuses).
    """

    def __init__(self, provider, budget: Budget, *, max_output_tokens: int) -> None:
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if getattr(provider, "max_tokens", max_output_tokens) is None:
            raise ValueError(
                "wrapped provider does not cap output tokens; a hard budget "
                "cap is impossible without max_tokens on the request"
            )
        self.provider = provider
        self.budget = budget
        self.max_output_tokens = max_output_tokens
        self.model = getattr(provider, "model", None)
        self.available = getattr(provider, "available", True)

    def complete_with_metadata(self, messages, *, seed=None):
        exact = count_prompt_tokens(messages)
        if exact is not None:
            estimated = exact
        else:
            prompt_text = "\n".join(str(m.get("content", "")) for m in messages)
            estimated = estimate_prompt_tokens(prompt_text)
        self.budget.check_request_fits(estimated, self.max_output_tokens, "provider request")
        kwargs = {"seed": seed} if seed is not None else {}
        completion = self.provider.complete_with_metadata(messages, **kwargs)
        actual = (completion.prompt_tokens or 0) + (completion.completion_tokens or 0)
        # If the provider reports no usage, charge the worst case.
        self.budget.charge(actual if actual else estimated + self.max_output_tokens,
                           "provider request")
        return completion

    def complete(self, messages):
        return self.complete_with_metadata(messages).text
