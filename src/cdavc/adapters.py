"""Offline output adapters, not vendor SDKs or hidden agent runtime integrations."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .accounting import Budget, UsageLedger, digest
from .patches import unified_diff_payload
from .payloads import parse_payload
from .providers import ProviderCompletion
from .verification import ArtifactStore, VerificationContract, WorkspaceSnapshot, verify_candidate


_LIMITATIONS = [
    "Source labels and upstream usage are self-reported exports, not independent vendor attestations.",
    "Include every upstream generation, retry, re-ask, summary, tool-model and judge call; omitted calls invalidate cost matching.",
    "Reasoning/cache counters are details of reported totals, not extra tokens to double-count.",
    "Verification makes zero model calls, but consumes local CPU, subprocess time and filesystem work.",
    "This is a frozen-artifact comparison, not a model-superiority or end-to-end generation experiment.",
    "Matching means identical declared caps, not identical actual spend; upstream compliance is reported, not enforced retroactively.",
]


def _telemetry(value: Mapping[str, Any] | None, budget: Budget) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping) or set(value) - {"calls", "complete", "wall_time_seconds", "limitations"}:
        raise ValueError("telemetry must use the documented export schema")
    complete = value.get("complete", False)
    calls = value.get("calls", [])
    if not isinstance(complete, bool) or not isinstance(calls, list):
        raise ValueError("telemetry complete must be boolean and calls must be an array")
    wall = value.get("wall_time_seconds")
    if wall is not None and (isinstance(wall, bool) or not isinstance(wall, (float, int)) or not math.isfinite(wall) or wall < 0):
        raise ValueError("telemetry wall_time_seconds must be finite and nonnegative")
    limitations = value.get("limitations", [])
    if not isinstance(limitations, list) or not all(isinstance(note, str) for note in limitations):
        raise ValueError("telemetry limitations must be strings")
    ledger = UsageLedger()
    for call in calls:
        if not isinstance(call, Mapping):
            raise ValueError("each exported call must be an object")
        counts = [call.get(name) for name in ("prompt_tokens", "completion_tokens")]
        if any(count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0) for count in counts):
            raise ValueError("exported token counts must be nonnegative integers or null")
        purpose = call.get("purpose", "external_generation")
        if not isinstance(purpose, str) or not purpose:
            raise ValueError("exported call purpose must be text")
        elapsed = call.get("wall_time_seconds", 0.0)
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("exported call duration must be finite and nonnegative")
        status = call.get("status", "completed")
        if status not in {"completed", "error"}:
            raise ValueError("exported call status must be completed or error")
        usage = call.get("usage", {})
        if not isinstance(usage, Mapping):
            raise ValueError("exported detailed usage must be an object")
        completion = ProviderCompletion("", *counts, model=call.get("model") if isinstance(call.get("model"), str) else None,
                                        metadata={"usage": usage})
        ledger.record(completion, purpose=purpose, request_digest="", elapsed=float(elapsed),
                      error=RuntimeError() if status == "error" else None)
        # Missing upstream payloads have unknown digests, not hashes of empty text.
        ledger.entries[-1].update(request_digest=None, response_digest=None)
    summary = ledger.summary()
    summary["usage_complete"] = bool(complete and summary["usage_complete"])
    if not summary["usage_complete"]:
        summary.update(token_in=None, token_out=None, total_tokens=None)
        summary["token_usage_source"] = "provider_partial" if summary["known_token_in"] or summary["known_token_out"] else "unavailable"
    summary["budget"] = budget.to_dict()
    bounded = any(limit is not None for limit in budget.to_dict().values())
    compliance = "unbounded"
    if bounded:
        checks = []
        if budget.max_calls is not None:
            checks.append(None if not complete else len(calls) <= budget.max_calls)
        if budget.max_tokens is not None:
            checks.append(None if not summary["usage_complete"] else summary["total_tokens"] <= budget.max_tokens)
        if budget.max_wall_seconds is not None:
            checks.append(None if wall is None or not complete else wall <= budget.max_wall_seconds)
        compliance = "exceeded" if False in checks else "unverifiable" if None in checks else "within_reported_cap"
    return {**summary, "provider_calls": len(calls) if complete else None, "reported_provider_calls": len(calls),
            "call_log": ledger.entries, "upstream_calls_complete": complete,
            "generation_wall_time_seconds": wall, "budget_compliance": compliance,
            "telemetry_limitations": _LIMITATIONS + limitations + ([] if complete else ["Upstream call inventory is incomplete."])}


def evaluate_external(snapshot: WorkspaceSnapshot, contract: VerificationContract, text: str, *, source: str,
                      format: str = "json", telemetry: Mapping[str, Any] | None = None, budget: Budget | None = None,
                      identifier: str | None = None, store: ArtifactStore | None = None,
                      timeout_seconds: float = 30, seed: int = 0) -> dict[str, Any]:
    if not isinstance(source, str) or not source.strip() or len(source) > 120 or any(ord(char) < 32 for char in source):
        raise ValueError("source must be a short, nonempty provenance label")
    identifier = source if identifier is None else identifier
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("candidate identifier must be nonempty text")
    budget = budget or Budget()
    usage = _telemetry(telemetry, budget)
    if format == "diff":
        with snapshot.materialize() as root:
            payload = unified_diff_payload(root, contract.implementation_files, text)
    elif format == "json":
        payload = parse_payload(text)
        if not isinstance(payload, dict):
            raise ValueError("candidate export must be a files/edits JSON object")
    else:
        raise ValueError("candidate format must be json or diff")
    evidence = verify_candidate(snapshot, payload, contract, store=store, seed=seed, timeout_seconds=timeout_seconds)
    engine = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(Path(__file__).parent.glob("*.py"))}
    experiment = {"schema": "external-artifact-comparison-v1", "snapshot_digest": snapshot.digest,
                  "contract_digest": evidence["contract_digest"], "budget": budget.to_dict(),
                  "engine": engine, "python": list(sys.version_info[:3]), "seed": seed, "timeout_seconds": timeout_seconds}
    record = {"schema": "cdavc.external-artifact.v1", "id": identifier, "source": source, "format": format,
              "experiment_fingerprint": digest(experiment), "experiment_config": experiment,
              "artifact_digest": evidence["artifact_digest"], "accepted": evidence["accepted"],
              "verification_evidence": evidence, "verification_model_calls": 0,
              "budget": budget.to_dict(), **usage}
    record["record_digest"] = digest(record)
    return record


def compare_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if isinstance(records, (str, bytes)) or len(records) < 2:
        raise ValueError("comparison requires at least two records")
    rows = json.loads(json.dumps(list(records), allow_nan=False))
    identifiers = [row.get("id") for row in rows]
    if any(not isinstance(value, str) or not value for value in identifiers) or len(set(identifiers)) != len(rows):
        raise ValueError("comparison identifiers must be unique nonempty strings")
    for row in rows:
        if row.get("schema") != "cdavc.external-artifact.v1":
            raise ValueError("incompatible external record schema")
        if row.get("record_digest") != digest({key: value for key, value in row.items() if key != "record_digest"}):
            raise ValueError("corrupt external record digest")
        config = row.get("experiment_config")
        if not isinstance(config, dict) or row.get("experiment_fingerprint") != digest(config):
            raise ValueError("incompatible or corrupt experiment fingerprint")
        evidence = row.get("verification_evidence", {})
        if evidence.get("evidence_digest") != digest({key: value for key, value in evidence.items() if key != "evidence_digest"}):
            raise ValueError("corrupt verification evidence digest")
    if len({row["experiment_fingerprint"] for row in rows}) != 1:
        raise ValueError("incompatible snapshots, contracts, engine versions or generation budgets")
    complete = all(row["usage_complete"] for row in rows)
    matched = complete and all(row["budget_compliance"] == "within_reported_cap" for row in rows)
    limitations = list(dict.fromkeys(note for row in rows for note in row["telemetry_limitations"]))
    report = {"schema": "cdavc.external-comparison.v1", "experiment_fingerprint": rows[0]["experiment_fingerprint"],
              "comparison_status": "matched_reported_budget" if matched else "inconclusive",
              "token_comparison_complete": complete, "budget": rows[0]["budget"],
              "scope": "Frozen artifacts evaluated identically under one snapshot and contract; no generation was performed.",
              "telemetry_limitations": limitations, "records": rows}
    report["report_digest"] = digest(report)
    return report


def render_comparison(report: Mapping[str, Any]) -> str:
    def display(value: Any) -> str:
        return "unknown" if value is None else str(value).replace("|", "\\|")

    lines = ["# External artifact comparison", "", str(report["scope"]), "",
             f"Budget matching: **{report['comparison_status']}** (self-reported upstream telemetry).",
             f"Shared caps: `{json.dumps(report['budget'], sort_keys=True)}`.", "",
             "| Candidate | Source | Accepted under checks | Provider calls | Input tokens | Output tokens | Budget compliance |",
             "|---|---|---|---:|---:|---:|---|"]
    for row in report["records"]:
        cells = [row["id"], row["source"], row["accepted"], row["provider_calls"], row["token_in"], row["token_out"], row["budget_compliance"]]
        lines.append("| " + " | ".join(display(value) for value in cells) + " |")
    lines += ["", "## Limitations", ""]
    lines += [f"- {note}" for note in report["telemetry_limitations"]]
    lines += ["", f"Report SHA-256: `{report['report_digest']}`.", ""]
    return "\n".join(lines)
