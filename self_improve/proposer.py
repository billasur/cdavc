"""Change proposers for the self-improvement loop.

ScriptedProposer is deterministic and offline: it walks one-knob mutations in
a fixed order. ModelProposer would ask a model to propose the next config;
it is a stub that refuses to run without explicit spend approval, because no
token spend is authorized for it.
"""

from __future__ import annotations

from .config import HarnessConfig, one_knob_mutations


class Proposer:
    def propose(self, current: HarnessConfig, tried: list[HarnessConfig], history: list[dict]) -> HarnessConfig | None:
        raise NotImplementedError


class ScriptedProposer(Proposer):
    """Cycles through every one-knob mutation not tried yet, in a fixed order."""

    def propose(self, current: HarnessConfig, tried: list[HarnessConfig], history: list[dict]) -> HarnessConfig | None:
        for candidate in one_knob_mutations(current):
            if candidate not in tried:
                return candidate
        return None


class ModelProposer(Proposer):
    """Placeholder for a model-driven proposer. Never runs without approval."""

    def __init__(self, *, spend_approved: bool = False) -> None:
        self.spend_approved = spend_approved

    def propose(self, current: HarnessConfig, tried: list[HarnessConfig], history: list[dict]) -> HarnessConfig | None:
        if not self.spend_approved:
            raise PermissionError(
                "ModelProposer spends tokens; no spend approval is on record. "
                "Use ScriptedProposer or get explicit approval first."
            )
        raise NotImplementedError("model-driven proposals are not implemented yet")
