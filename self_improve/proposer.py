"""Change proposers for the self-improvement loop.

ScriptedProposer is deterministic and offline: it walks one-knob mutations in
a fixed order. ModelProposer asks a model for the next config, grounded in the
loop's measured history. Both are constrained to the validated config surface:
a ModelProposer output that does not parse as a valid HarnessConfig is
rejected, so the model can never widen the editable surface or touch the
evaluator.

ModelProposer spends tokens. It refuses to run unless constructed with
spend_approved=True; run.py wires that flag to --approve-spend, and the pi
extension never enables it.
"""

from __future__ import annotations

import json

from .config import ConfigError, HarnessConfig, one_knob_mutations


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


MODEL_PROPOSER_PROMPT = """You are tuning a deterministic code-verification harness (CD-AVC).
You may ONLY choose the next harness config. You cannot change tests,
grading, or the task set.

Allowed knobs and bounds:
- retry_cap: integer 0..3 (max feedback-repair attempts per task)
- prompt_layout: "default" or "stable-prefix"
- lenient_parse: true or false (repair truncated model JSON before parsing)

Current config: {current}

Measured history (config -> passes/total, tokens; provisional single-seed):
{history}

Already tried (do not repeat): {tried}

Rules:
- Pick a config that is plausibly better at EQUAL total token cost. More
  retries only count if the extra passes come at no greater total spend.
- Reply with ONLY one JSON object with exactly these three keys:
  {{"retry_cap": int, "prompt_layout": str, "lenient_parse": bool}}
- If nothing untried is worth testing, reply with exactly: null"""


class ModelProposer(Proposer):
    """Asks a provider for the next config. Output is parsed and validated
    through HarnessConfig.from_dict, so anything outside the bounded surface
    (extra keys, out-of-range values, prose) is rejected. One re-ask on an
    invalid reply, then None (loop stops instead of guessing)."""

    def __init__(self, provider, *, spend_approved: bool = False) -> None:
        if not spend_approved:
            raise PermissionError(
                "ModelProposer spends tokens; construct it only with "
                "spend_approved=True after explicit approval."
            )
        self.provider = provider

    def _ask(self, prompt: str) -> str:
        completion = self.provider.complete_with_metadata(
            [{"role": "user", "content": prompt}])
        return completion.text if hasattr(completion, "text") else str(completion)

    @staticmethod
    def _parse(reply: str) -> HarnessConfig | None:
        text = reply.strip()
        if text == "null":
            return None
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        return HarnessConfig.from_dict(json.loads(text))

    def propose(self, current: HarnessConfig, tried: list[HarnessConfig], history: list[dict]) -> HarnessConfig | None:
        prompt = MODEL_PROPOSER_PROMPT.format(
            current=current.to_json().strip(),
            history=json.dumps(history, indent=1) or "(none yet)",
            tried=json.dumps([c.to_runner_kwargs() for c in tried]),
        )
        for _ in range(2):  # one re-ask on an invalid reply
            reply = self._ask(prompt)
            try:
                candidate = self._parse(reply)
            except (json.JSONDecodeError, ConfigError, TypeError):
                prompt = ("Your last reply was not a valid config. "
                          "Reply with ONLY the JSON object, or null.\n\n" + prompt)
                continue
            if candidate is None:
                return None
            if candidate in tried:
                prompt = (f"Config {candidate.to_runner_kwargs()} was already "
                          "tried. Pick a different one, or null.\n\n" + prompt)
                continue
            return candidate
        return None
