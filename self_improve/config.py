"""Bounded harness configuration: the ONLY surface the improving agent may edit.

Every knob maps to an existing BenchmarkRunner argument; no knob can change
tests, grading, or the task set. Validation rejects anything outside the
declared bounds so a proposed change can never widen the surface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


class ConfigError(ValueError):
    """A proposed harness config is outside the allowed surface."""


PROMPT_LAYOUTS = ("default", "stable-prefix")


@dataclass(frozen=True)
class HarnessConfig:
    retry_cap: int = 3            # BenchmarkRunner retry_cap, bounds 0..3
    prompt_layout: str = "default"  # BenchmarkRunner prompt_layout
    lenient_parse: bool = True    # BenchmarkRunner lenient_parse

    def validate(self) -> "HarnessConfig":
        if isinstance(self.retry_cap, bool) or not isinstance(self.retry_cap, int) or not 0 <= self.retry_cap <= 3:
            raise ConfigError(f"retry_cap must be an int in 0..3, got {self.retry_cap!r}")
        if self.prompt_layout not in PROMPT_LAYOUTS:
            raise ConfigError(f"prompt_layout must be one of {PROMPT_LAYOUTS}, got {self.prompt_layout!r}")
        if not isinstance(self.lenient_parse, bool):
            raise ConfigError(f"lenient_parse must be a bool, got {self.lenient_parse!r}")
        return self

    def to_runner_kwargs(self) -> dict:
        return {
            "retry_cap": self.retry_cap,
            "prompt_layout": self.prompt_layout,
            "lenient_parse": self.lenient_parse,
        }

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, payload: dict) -> "HarnessConfig":
        allowed = {"retry_cap", "prompt_layout", "lenient_parse"}
        unknown = set(payload) - allowed
        if unknown:
            raise ConfigError(f"unknown config keys (outside editable surface): {sorted(unknown)}")
        return cls(**payload).validate()

    @classmethod
    def load(cls, path: Path) -> "HarnessConfig":
        return cls.from_dict(json.loads(Path(path).read_text()))


def one_knob_mutations(config: HarnessConfig) -> list[HarnessConfig]:
    """Every config exactly one knob away from `config`, inside the bounds."""
    out: list[HarnessConfig] = []
    for rc in (0, 1, 2, 3):
        if rc != config.retry_cap:
            out.append(HarnessConfig(rc, config.prompt_layout, config.lenient_parse))
    for layout in PROMPT_LAYOUTS:
        if layout != config.prompt_layout:
            out.append(HarnessConfig(config.retry_cap, layout, config.lenient_parse))
    out.append(HarnessConfig(config.retry_cap, config.prompt_layout, not config.lenient_parse))
    return [c.validate() for c in out]
