"""Bounded, frozen-candidate diagnostics using the shared verifier.

Constructed adversarial examples are diagnostic demonstrations, not held-out
model evaluations, market evidence, or a security sandbox.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import tempfile

from .properties import PropertyCase
from .verification import VERIFIER_VERSION, VerificationContract, WorkspaceSnapshot, verify_candidate


_SCOPE = "Fixed, intentionally constructed adversarial candidate fixtures; not held-out model or market evidence."
_LIMITATIONS = [
    "Results describe only these labelled examples and declared checks; they do not estimate generalization or model quality.",
    "Ground truth is supplied by fixture authors, not inferred by the verifier.",
    "Fresh temporary projects and subprocesses are isolation, not sandboxing arbitrary Python; use trusted fixtures only.",
    "Rates use all fixtures of the relevant truth class; inconclusive and environmental outcomes are reported separately.",
    "Reproducibility assumes the same Python/runtime and verifier version; timing and temporary paths are excluded.",
]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _validate(fixtures):
    if type(fixtures) is not list or not 2 <= len(fixtures) <= 32:
        raise ValueError("fixtures must be a list of 2 to 32 cases containing both truth classes")
    try:
        encoded = _canonical(fixtures)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("fixtures must contain finite JSON values") from exc
    if len(encoded.encode()) > 256_000:
        raise ValueError("fixture configuration exceeds 256000 bytes")
    # Freeze an independent JSON copy before validating or executing anything.
    frozen = json.loads(encoded)
    seen, classes, prepared = set(), set(), []
    required = {"id", "label", "ground_truth_correct", "files", "public_check", "properties"}
    for fixture in frozen:
        if type(fixture) is not dict or not required <= fixture.keys() or fixture.keys() - required - {"symbols", "invariants", "timeout_seconds"}:
            raise ValueError("fixture fields are missing or unknown")
        for key in ("id", "label", "public_check"):
            if type(fixture[key]) is not str or not fixture[key].strip() or len(fixture[key]) > (16000 if key == "public_check" else 200):
                raise ValueError(f"invalid fixture {key}")
        if fixture["id"] in seen:
            raise ValueError("duplicate fixture id")
        seen.add(fixture["id"])
        if type(fixture["ground_truth_correct"]) is not bool:
            raise ValueError("ground_truth_correct must be boolean")
        classes.add(fixture["ground_truth_correct"])
        files = fixture["files"]
        if type(files) is not dict or not 1 <= len(files) <= 8:
            raise ValueError("files must contain 1 to 8 Python source files")
        for name, source in files.items():
            path = PurePosixPath(name)
            if (path.is_absolute() or ".." in path.parts or path.as_posix() != name or path.suffix != ".py"
                    or "\\" in name or "\x00" in name or any(part.startswith(".") for part in path.parts)
                    or name == "public_check.py" or type(source) is not str):
                raise ValueError("invalid candidate source path or content")
        properties = fixture["properties"]
        if type(properties) is not list or not 1 <= len(properties) <= 16:
            raise ValueError("properties must contain 1 to 16 explicit cases")
        for field in ("symbols", "invariants"):
            values = fixture.get(field, [])
            if type(values) is not list or not all(type(value) is str and value for value in values):
                raise ValueError(f"{field} must be a list of non-empty strings")
        timeout = fixture.get("timeout_seconds", 2.0)
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 5:
            raise ValueError("fixture timeout_seconds must be finite and in (0, 5]")
        coarse = VerificationContract(implementation_files=tuple(sorted(files)), test_files=("public_check.py",),
                                      symbols=tuple(fixture.get("symbols", [])), invariants=tuple(fixture.get("invariants", [])),
                                      test_command=("python", "public_check.py"))
        enhanced = replace(coarse, properties=tuple(PropertyCase.from_dict(case) for case in properties))
        prepared.append((fixture, coarse, enhanced, timeout))
    if classes != {True, False}:
        raise ValueError("fixtures must include both correct and incorrect truth classes")
    return frozen, prepared


def _metrics(cases, arm):
    correct = sum(case["ground_truth_correct"] for case in cases)
    incorrect = len(cases) - correct
    wrong = sum(not case["ground_truth_correct"] and case[arm]["accepted"] for case in cases)
    rejections = sum(case["ground_truth_correct"] and case[arm]["outcome"] == "rejected_with_counterexample" for case in cases)
    inconclusive = sum(case[arm]["outcome"] == "inconclusive" for case in cases)
    environment = sum(case[arm]["outcome"] == "environment_failure" for case in cases)
    conclusive = len(cases) - inconclusive - environment
    return dict(total=len(cases), correct_fixtures=correct, incorrect_fixtures=incorrect,
                accepted=sum(case[arm]["accepted"] for case in cases), wrong_acceptances=wrong,
                wrong_acceptance_rate=wrong / incorrect, correct_rejections=rejections,
                correct_rejection_rate=rejections / correct, inconclusive=inconclusive,
                environment_failures=environment, conclusive=conclusive, coverage=conclusive / len(cases))


def run_fixture_audit(fixtures: list[dict], *, max_correct_rejection_increase: float = 0.0) -> dict:
    """Measure coarse versus property-augmented contracts once per frozen case.

    Correct rejections count explicit rejected_with_counterexample outcomes;
    environment/inconclusive outcomes are separate and prevent criterion success.
    All validation completes before executing source. At most 32 cases, 8 source
    files, 16 properties and a 5-second per-check timeout are permitted.
    """
    threshold = max_correct_rejection_increase
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("max_correct_rejection_increase must be a finite rate in [0, 1]")
    frozen, prepared = _validate(fixtures)
    cases = []
    for fixture, coarse, enhanced, timeout in prepared:
        with tempfile.TemporaryDirectory(prefix="cdavc-fixture-") as directory:
            root = Path(directory)
            (root / "public_check.py").write_text(fixture["public_check"], encoding="utf-8")
            snapshot = WorkspaceSnapshot.capture(root)
            payload = {"files": fixture["files"]}
            row = {key: fixture[key] for key in ("id", "label", "ground_truth_correct")}
            for arm, contract in (("coarse", coarse), ("properties", enhanced)):
                row[arm] = verify_candidate(snapshot, payload, contract, timeout_seconds=timeout)
            cases.append(row)
    arms = {arm: _metrics(cases, arm) for arm in ("coarse", "properties")}
    delta = {key: arms["properties"][key] - arms["coarse"][key] for key in
             ("wrong_acceptances", "wrong_acceptance_rate", "correct_rejections", "correct_rejection_rate")}
    criterion = (delta["wrong_acceptances"] < 0 and delta["correct_rejection_rate"] <= threshold
                 and all(arm["coverage"] == 1 for arm in arms.values()))
    report = dict(schema="cdavc.fixture-audit.v1", verifier_version=VERIFIER_VERSION, fixture_digest=_digest(frozen),
                  fixture_count=len(cases), scope=_SCOPE, limitations=list(_LIMITATIONS),
                  max_correct_rejection_increase=float(threshold), arms=arms, delta=delta,
                  acceptance_criterion_met=criterion, cases=cases)
    report["report_digest"] = _digest(report)
    return report


def render_fixture_report(report: dict) -> str:
    """Render measured results, preserving the diagnostic's explicit scope."""
    lines = ["# Frozen-candidate verifier diagnostic", "", report["scope"], "",
             f"Fixture configuration SHA-256: `{report['fixture_digest']}`",
             f"Report SHA-256: `{report['report_digest']}`", "",
             "| Contract | Wrong acceptances / incorrect | Correct rejections / correct | Inconclusive | Environment | Coverage |",
             "| --- | --- | --- | --- | --- | --- |"]
    for name, arm in report["arms"].items():
        lines.append(f"| {name} | {arm['wrong_acceptances']}/{arm['incorrect_fixtures']} ({arm['wrong_acceptance_rate']:.1%}) | "
                     f"{arm['correct_rejections']}/{arm['correct_fixtures']} ({arm['correct_rejection_rate']:.1%}) | "
                     f"{arm['inconclusive']} | {arm['environment_failures']} | {arm['coverage']:.1%} |")
    lines.extend(["", f"Acceptance criterion met: **{report['acceptance_criterion_met']}**.",
                  f"Correct-rejection rate increase allowed: {report['max_correct_rejection_increase']:.1%}.",
                  f"Measured property-minus-coarse deltas: `{_canonical(report['delta'])}`.", "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.extend(["", "## Case evidence", ""])
    for case in report["cases"]:
        lines.append(f"- {case['id']} (correct={case['ground_truth_correct']}): {case['label']}")
        for arm in ("coarse", "properties"):
            evidence = case[arm]
            lines.append(f"  - {arm}: {evidence['outcome']}; artifact `{evidence['artifact_digest']}`; evidence `{evidence['evidence_digest']}`")
    return "\n".join(lines) + "\n"
