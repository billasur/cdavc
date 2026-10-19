"""Re-verify stored candidates offline, without spending a single model token.

Every cdavc record keeps the exact files the model produced under
``results/candidates/<arm>/<task_id>/<sha>/``.  This module replays those
candidates through the same gates the live run applied, so a verifier change
can be measured against a fixed candidate pool instead of against a fresh
(and therefore differently-sampled) generation.

Usage::

    PYTHONPATH=src python -m cdavc.replay results/benchmark30.jsonl

    --root .            project root the gates run against
    --tasks PATH        task corpus (default: <root>/benchmarks/tasks.json)
    --out PATH          JSONL destination (default: <records dir>/replay.jsonl)
    --arm NAME          arm to replay (default: cdavc; "all" replays every arm)
    --mutants N         generate N mutants per candidate in the property gate
    --seed N            property-gate seed, read from the record when omitted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .benchmark import ARMS, BenchmarkError, BenchmarkRunner, load_tasks, read_records

REPLAY_VERSION = "1"


def _records_dir(records_path: Path) -> Path:
    return records_path.resolve().parent


def select_records(
    records: Sequence[Mapping[str, Any]],
    *,
    arm: str = "cdavc",
) -> list[dict[str, Any]]:
    """Return the latest record per (task, arm) that kept a candidate on disk."""

    if arm != "all" and arm not in ARMS:
        raise BenchmarkError(f"unknown benchmark arm: {arm}")
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        record_arm = str(record.get("arm"))
        if arm != "all" and record_arm != arm:
            continue
        if not isinstance(record.get("candidate_dir"), str) or not record["candidate_dir"]:
            continue
        latest[(str(record.get("task_id")), record_arm)] = dict(record)
    return [latest[key] for key in sorted(latest)]


def replay_records(
    records_path: Path | str,
    *,
    root: Path | str = ".",
    tasks_path: Path | str | None = None,
    out_path: Path | str | None = None,
    arm: str = "cdavc",
    mutants: int = 0,
) -> dict[str, Any]:
    """Re-verify every stored candidate and write one JSON line per record."""

    records_file = Path(records_path)
    if not records_file.is_file():
        raise BenchmarkError(f"records file does not exist: {records_file}")
    root_dir = Path(root).resolve()
    corpus = Path(tasks_path) if tasks_path is not None else root_dir / "benchmarks" / "tasks.json"
    tasks = {task.task_id: task for task in load_tasks(corpus)}
    records_dir = _records_dir(records_file)
    destination = Path(out_path) if out_path is not None else records_dir / "replay.jsonl"
    if not destination.is_absolute():
        destination = (Path.cwd() / destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    selected = select_records(read_records(records_file), arm=arm)
    seeds = {int(record.get("seed", 0)) for record in selected}
    seed = seeds.pop() if len(seeds) == 1 else 0

    dummy_provider = lambda _arm, _task: None  # noqa: E731 - replay never calls a model
    runner = BenchmarkRunner(
        root_dir,
        dummy_provider,
        tasks=list(tasks.values()),
        records_path=records_file,
        seed=seed,
        retry_cap=0,
        samples=1,
        mutants=mutants,
    )

    outcomes: list[dict[str, Any]] = []
    skipped: list[str] = []
    with destination.open("w", encoding="utf-8") as handle:
        for record in selected:
            task_id = str(record.get("task_id"))
            task = tasks.get(task_id)
            if task is None:
                skipped.append(f"{task_id}: not in {corpus}")
                continue
            candidate_dir = Path(str(record["candidate_dir"]))
            if not candidate_dir.is_absolute():
                candidate_dir = records_dir / candidate_dir
            if not candidate_dir.is_dir():
                skipped.append(f"{task_id}: candidate directory missing ({candidate_dir})")
                continue
            result = runner.verify_candidate(task, candidate_dir)
            properties = result.get("properties") or {}
            outcome = {
                "task_id": task_id,
                "arm": record.get("arm"),
                "original_pass": bool(record.get("pass") or record.get("passed")),
                "replay_pass": bool(result.get("passed")),
                "failure": result.get("failure") or "",
                "gate_results": list(result.get("gate_results") or ()),
                "candidate_sha": record.get("candidate_sha"),
                "property_failures": list(properties.get("failures") or ()),
                "mutant_kill_rate": (properties.get("mutants") or {}).get("kill_rate"),
                "replay_version": REPLAY_VERSION,
            }
            outcomes.append(outcome)
            handle.write(json.dumps(outcome, sort_keys=True) + "\n")

    original = sum(1 for outcome in outcomes if outcome["original_pass"])
    replayed = sum(1 for outcome in outcomes if outcome["replay_pass"])
    mismatches = [
        outcome["task_id"] for outcome in outcomes if outcome["original_pass"] != outcome["replay_pass"]
    ]
    summary = {
        "records_path": str(records_file),
        "out_path": str(destination),
        "arm": arm,
        "replayed": len(outcomes),
        "skipped": skipped,
        "original_passes": original,
        "replay_passes": replayed,
        "mismatches": mismatches,
        "outcomes": outcomes,
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdavc.replay",
        description="Re-verify stored candidates offline (no model calls).",
    )
    parser.add_argument("records", type=Path, help="benchmark records JSONL with stored candidates")
    parser.add_argument("--root", type=Path, default=Path("."), help="project root the gates run against")
    parser.add_argument("--tasks", type=Path, default=None, help="task corpus (default: <root>/benchmarks/tasks.json)")
    parser.add_argument("--out", type=Path, default=None, help="JSONL destination (default: <records dir>/replay.jsonl)")
    parser.add_argument("--arm", default="cdavc", help="arm to replay, or 'all' (default: cdavc)")
    parser.add_argument("--mutants", type=int, default=0, help="mutants per candidate in the property gate")
    return parser


def render_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        f"replayed {summary['replayed']} candidate(s) from {summary['records_path']}",
        f"original passes {summary['original_passes']} -> replay passes {summary['replay_passes']}",
    ]
    mismatches = list(summary.get("mismatches") or ())
    if mismatches:
        lines.append(f"mismatches ({len(mismatches)}): {', '.join(mismatches)}")
    else:
        lines.append("mismatches: none")
    for skipped in summary.get("skipped") or ():
        lines.append(f"skipped: {skipped}")
    lines.append(f"wrote {summary['out_path']}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = replay_records(
            args.records,
            root=args.root,
            tasks_path=args.tasks,
            out_path=args.out,
            arm=args.arm,
            mutants=args.mutants,
        )
    except (OSError, ValueError, BenchmarkError) as exc:
        print(f"cdavc replay: {exc}", file=sys.stderr)
        return 2
    print(render_summary(summary), end="")
    return 0 if not summary["mismatches"] else 1


__all__ = [
    "REPLAY_VERSION",
    "build_parser",
    "main",
    "render_summary",
    "replay_records",
    "select_records",
]

if __name__ == "__main__":  # pragma: no cover - thin CLI wrapper
    raise SystemExit(main())
