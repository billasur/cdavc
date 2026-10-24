"""Cumulative token budget for a supervised self-improvement run.

One budget covers EVERYTHING the run spends: model-proposer calls, seed-1
evaluations, and multi-seed validation re-runs. Accounting uses measured
usage after each evaluation; because a single evaluation can overshoot
between accounting points, no new evaluation starts once the soft threshold
(80% of the cap) is consumed. The hard cap is the user's approved number.
"""

from __future__ import annotations


class BudgetExhausted(RuntimeError):
    """The soft threshold is consumed; no new evaluation may start."""


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

    def summary(self) -> str:
        return f"{self.spent}/{self.cap} tokens spent (soft limit {self.soft_limit})"
