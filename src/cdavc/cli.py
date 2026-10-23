"""Command-line entry point for the task-graph runner and one-shot changes."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from importlib import metadata
from pathlib import Path

from .graph import TaskGraph
from .providers import MockProvider, OpenAICompatibleProvider, ProviderUnavailableError, SamplingParams
from .supervisor import Supervisor
from .accounting import Budget


def _version() -> str:
    try:
        return metadata.version("cdavc")
    except metadata.PackageNotFoundError:
        return "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdavc",
        description="Run contract-driven changes or verify frozen agent outputs with one local verifier.",
        epilog=(
            "Describe one change without writing a task graph:\n"
            "  cdavc run \"add discount support to total()\" \\\n"
            "      --file src/shop/pricing.py --test tests/test_pricing.py\n\n"
            "Preview the verified patch without touching the project:\n"
            "  cdavc run \"...\" --file ... --test ... --dry-run\n\n"
            "Run a real model instead of the scripted mock:\n"
            "  cdavc task_graph.json --provider openai \\\n"
            "      --endpoint http://127.0.0.1:8080/v1/chat/completions --model local-model\n\n"
            "Offline artifact workflows (no generation):\n"
            "  cdavc verify --help\n"
            "  cdavc compare --help\n"
            "  cdavc audit-fixtures --help"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("graph", type=Path, help="path to task_graph.json")
    parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    parser.add_argument("--mock-response", action="append", default=[], help="JSON response file; may be repeated")
    parser.add_argument("--endpoint", default=os.environ.get("CDAVC_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("CDAVC_MODEL", "local-model"))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("CDAVC_TIMEOUT", "30")), help="provider request timeout in seconds")
    parser.add_argument("--test-timeout", type=float, default=120.0, help="seconds allowed per verification command (default: 120)")
    parser.add_argument("--dry-run", action="store_true", help="verify the change and print the patch without writing it to the project")
    parser.add_argument("--quiet", action="store_true", help="suppress progress lines")
    parser.add_argument("--version", action="version", version=f"cdavc {_version()}")
    _sampling_options(parser)
    _execution_options(parser)
    return parser


def build_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdavc run",
        description=(
            "Describe one change in plain language. cdavc hands it to a local model in a throwaway copy of the "
            "project and keeps the result only after your tests, the syntax gate and the regression suite accept it."
        ),
        epilog=(
            "Example:\n"
            "  cdavc run \"add discount support to total()\" \\\n"
            "      --file src/shop/pricing.py --test tests/test_pricing.py \\\n"
            "      --invariant \"total(items, discount_rate=0.1) applies the discount before tax\" \\\n"
            "      --regression \"python -m pytest -q\"\n\n"
            "Every declared test file must already exist: cdavc only ships a change a test has approved."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", help="what to change, in one sentence")
    parser.add_argument("--file", dest="files", action="append", default=[], required=True, metavar="PATH", help="implementation file the model may change; repeat for several")
    parser.add_argument("--test", dest="tests", action="append", default=[], required=True, metavar="PATH", help="existing test file that defines done; repeat for several")
    parser.add_argument("--symbol", action="append", default=[], metavar="NAME", help="symbol that must exist afterwards (checked for Python files)")
    parser.add_argument("--invariant", action="append", default=[], metavar="TEXT", help="contract sentence the change must satisfy; repeatable")
    parser.add_argument("--test-command", metavar="CMD", help="targeted test command (default: unittest discover when tests/ exists); a leading NAME=value word is applied as environment")
    parser.add_argument("--regression", metavar="CMD", help="full project suite, for example 'python -m pytest -q'")
    parser.add_argument("--max-retries", type=int, default=2, help="repair attempts after a rejected candidate (default: 2)")
    parser.add_argument("--samples", type=int, default=1, metavar="N", help="draw at least N candidates before giving up (default: 1; each draw after the first is told why the one before it was rejected)")
    parser.add_argument("--directory", type=Path, default=Path.cwd(), metavar="DIR", help="project root (default: current directory)")
    parser.add_argument("--test-timeout", type=float, default=120.0, help="seconds allowed per verification command (default: 120)")
    parser.add_argument("--dry-run", action="store_true", help="verify and print the patch without writing it to the project")
    parser.add_argument("--provider", choices=("openai", "mock"), default=None, help="model backend (default: mock when --mock-response is given, otherwise openai)")
    parser.add_argument("--mock-response", action="append", default=[], help="JSON response file; may be repeated")
    parser.add_argument("--endpoint", default=os.environ.get("CDAVC_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("CDAVC_MODEL", "local-model"))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("CDAVC_TIMEOUT", "300")), help="provider request timeout in seconds")
    parser.add_argument("--quiet", action="store_true", help="suppress progress lines and the patch")
    parser.add_argument("--version", action="version", version=f"cdavc {_version()}")
    parser.add_argument("--context-file", action="append", default=[], help="additional public caller/dependency source; repeatable")
    parser.add_argument("--property-file", type=Path, help="JSON array of executable contract cases")
    parser.add_argument("--check-repeats", type=int, default=1, help="fresh repeats per check, 1–5; disagreement is inconclusive")
    _sampling_options(parser)
    _execution_options(parser)
    return parser


def _execution_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-calls", type=int, help="per-task provider call cap, including retrieval")
    parser.add_argument("--max-tokens", type=int, help="per-task reported input+output token cap; missing usage is inconclusive")
    parser.add_argument("--max-wall-seconds", type=float, help="per-task wall-clock cap, checked between operations")
    parser.add_argument("--context-budget", dest="context_budget_chars", type=int, default=12000,
                        help="source-context character budget (not an estimated token count)")
    parser.add_argument("--max-context-requests", type=int, default=2, help="retrieval requests per draw (default: 2)")


def _sampling_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--temperature", type=float, help="sampling temperature sent to the model server")
    parser.add_argument("--top-p", type=float, help="nucleus sampling bound sent to the model server")
    parser.add_argument("--top-k", type=int, help="top-k sampling bound; accepted by llama.cpp, LM Studio, vLLM and Ollama")
    parser.add_argument("--max-output-tokens", type=int, help="completion length cap; a reply cut by this limit is rejected, not parsed")


def _execution_kwargs(args: argparse.Namespace) -> dict:
    return {"budget": Budget(args.max_calls, args.max_tokens, args.max_wall_seconds),
            "context_budget_chars": args.context_budget_chars, "max_context_requests": args.max_context_requests}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "run":
        return _run_task_command(arguments[1:])
    if arguments and arguments[0] == "audit-fixtures":
        return _audit_fixtures_command(arguments[1:])
    if arguments and arguments[0] == "verify":
        return _verify_export_command(arguments[1:])
    if arguments and arguments[0] == "compare":
        return _compare_exports_command(arguments[1:])
    args = build_parser().parse_args(arguments)
    location = str(args.graph)
    try:
        provider = _provider(args)
        supervisor = Supervisor(args.graph, provider, timeout_seconds=args.test_timeout, dry_run=args.dry_run,
                                on_event=None if args.quiet else _progress, **_execution_kwargs(args))
        result = supervisor.run()
    except ProviderUnavailableError as exc:
        return _provider_failure(args, location, exc)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"cdavc: {location}: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        _print_patch(result)
    return _status(result, location, args.graph.resolve().parent, dry_run=args.dry_run)


def _audit_fixtures_command(argv: list[str]) -> int:
    from .diagnostics import render_fixture_report, run_fixture_audit
    parser = argparse.ArgumentParser(prog="cdavc audit-fixtures", description="Measure verifier behaviour on fixed labelled artifacts; no model calls")
    parser.add_argument("--fixtures", type=Path, default=Path("benchmarks/verifier_fixtures.json"))
    parser.add_argument("--output", type=Path, default=Path("results/verifier-diagnostic.json"))
    parser.add_argument("--max-correct-rejection-increase", type=float, default=0.0)
    args = parser.parse_args(argv)
    try:
        if args.output.suffix != ".json" or args.output.resolve() == args.fixtures.resolve():
            raise ValueError("output must be a separate .json report")
        report = run_fixture_audit(json.loads(args.fixtures.read_text()),
            max_correct_rejection_increase=args.max_correct_rejection_increase)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        text = render_fixture_report(report)
        args.output.with_suffix(".md").write_text(text)
        print(text, end="")
        return 0 if report["acceptance_criterion_met"] else 1
    except (ValueError, OSError) as exc:
        print(f"cdavc audit-fixtures: {exc}", file=sys.stderr)
        return 2


def _write_json_report(path: Path, payload: dict, text: str | None = None) -> None:
    if path.suffix != ".json":
        raise ValueError("report output must end in .json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    if text is not None:
        path.with_suffix(".md").write_text(text)


def _verify_export_command(argv: list[str]) -> int:
    from .adapters import evaluate_external
    from .verification import ArtifactStore, VerificationContract, WorkspaceSnapshot
    parser = argparse.ArgumentParser(prog="cdavc verify", description="Verify an exported JSON/edit/diff artifact without calling a model or publishing changes")
    parser.add_argument("--directory", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--source", required=True, help="provenance label, e.g. claude, codex or local; not a vendor attestation")
    parser.add_argument("--format", choices=("json", "diff"), default="json")
    parser.add_argument("--telemetry", type=Path, help="optional upstream per-call usage export")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--test-timeout", type=float, default=30)
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--max-wall-seconds", type=float)
    args = parser.parse_args(argv)
    try:
        root = args.directory.resolve()
        output = args.output or root / "results/verification.json"
        if output.resolve() in {args.contract.resolve(), args.candidate.resolve(), args.telemetry.resolve() if args.telemetry else None}:
            raise ValueError("report cannot overwrite an input export")
        contract = VerificationContract.from_dict(json.loads(args.contract.read_text()))
        usage = json.loads(args.telemetry.read_text()) if args.telemetry else None
        row = evaluate_external(WorkspaceSnapshot.capture(root), contract, args.candidate.read_bytes().decode("utf-8"),
            source=args.source, format=args.format, telemetry=usage,
            budget=Budget(args.max_calls, args.max_tokens, args.max_wall_seconds),
            store=ArtifactStore(root / ".cdavc/artifacts"), timeout_seconds=args.test_timeout)
        _write_json_report(output, row)
        print(json.dumps(row, indent=2))
        return 0 if row["accepted"] and row["budget_compliance"] in {"unbounded", "within_reported_cap"} else 1
    except (OSError, ValueError, TypeError) as exc:
        print(f"cdavc verify: {exc}", file=sys.stderr)
        return 2


def _compare_exports_command(argv: list[str]) -> int:
    from .adapters import compare_records, evaluate_external, render_comparison
    from .edits import _safe_target
    from .verification import ArtifactStore, VerificationContract, WorkspaceSnapshot
    parser = argparse.ArgumentParser(prog="cdavc compare", description="Compare frozen exports under one contract and declared generation budget; no model calls")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        if not isinstance(manifest, dict) or set(manifest) - {"directory", "contract", "budget", "candidates", "seed", "timeout_seconds"}:
            raise ValueError("invalid comparison manifest")
        root = (args.manifest.resolve().parent / manifest.get("directory", ".")).resolve()
        inputs = {args.manifest.resolve()}

        def read_input(relative: str) -> str:
            path = _safe_target(root, relative)
            inputs.add(path.resolve())
            return path.read_bytes().decode("utf-8")

        contract = VerificationContract.from_dict(json.loads(read_input(manifest["contract"])))
        limits = manifest.get("budget", {})
        if not isinstance(limits, dict) or set(limits) - {"max_calls", "max_tokens", "max_wall_seconds"}:
            raise ValueError("invalid comparison budget")
        budget = Budget(**limits)
        candidates = manifest.get("candidates")
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 32:
            raise ValueError("comparison needs 2 to 32 candidate exports")
        prepared = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or set(candidate) - {"id", "source", "candidate", "format", "telemetry"}:
                raise ValueError("invalid candidate manifest entry")
            text = read_input(candidate["candidate"])
            usage = json.loads(read_input(candidate["telemetry"])) if candidate.get("telemetry") else None
            prepared.append((candidate, text, usage))
        output = args.output or root / "results/comparison.json"
        if output.resolve() in inputs or output.with_suffix(".md").resolve() in inputs:
            raise ValueError("comparison report cannot overwrite an input")
        snapshot = WorkspaceSnapshot.capture(root)
        store = ArtifactStore(root / ".cdavc/artifacts")
        records = [evaluate_external(snapshot, contract, text, source=candidate["source"],
            identifier=candidate["id"], format=candidate.get("format", "json"), telemetry=usage,
            budget=budget, store=store, seed=manifest.get("seed", 0), timeout_seconds=manifest.get("timeout_seconds", 30))
            for candidate, text, usage in prepared]
        report = compare_records(records)
        text = render_comparison(report)
        _write_json_report(output, report, text)
        print(text, end="")
        return 0 if report["comparison_status"] == "matched_reported_budget" else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"cdavc compare: {exc}", file=sys.stderr)
        return 2


def _run_task_command(argv: list[str]) -> int:
    args = build_run_parser().parse_args(argv)
    root = args.directory.resolve()
    location = args.task
    if not root.is_dir():
        print(f"cdavc: {root}: project directory does not exist", file=sys.stderr)
        return 2
    try:
        missing = [path for path in args.tests if not (root / path).is_file()]
        if missing:
            raise ValueError(f"declared test file does not exist: {missing[0]} (write the test first; cdavc verifies against it)")
        test_command = _command(args.test_command)
        if test_command is None and (root / "tests").is_dir():
            test_command = ("python", "-m", "unittest", "discover", "-s", "tests")
        regression_command = _command(args.regression)
        if regression_command is None and (root / "tests").is_dir():
            regression_command = ("python", "-m", "unittest", "discover", "-s", "tests")
        properties = json.loads(args.property_file.read_text()) if args.property_file else []
        graph = TaskGraph.from_dict(
            {
                "project_id": root.name or "cdavc-task",
                "tasks": [
                    {
                        "id": "T1",
                        "title": args.task,
                        "implementation_files": args.files,
                        "test_files": args.tests,
                        "symbols": args.symbol,
                        "invariants": args.invariant,
                        "test_command": test_command,
                        "regression_command": regression_command,
                        "max_retries": args.max_retries,
                        "properties": properties,
                        "check_repeats": args.check_repeats,
                        "context_files": args.context_file,
                    }
                ],
            }
        )
        provider = _provider(args)
        supervisor = Supervisor(None, provider, graph=graph, root=root, timeout_seconds=args.test_timeout, dry_run=args.dry_run,
                                on_event=None if args.quiet else _progress, samples=args.samples, **_execution_kwargs(args))
        result = supervisor.run()
    except ProviderUnavailableError as exc:
        return _provider_failure(args, location, exc)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"cdavc: {location}: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        _print_patch(result)
    return _status(result, location, root, dry_run=args.dry_run)


def _provider(args: argparse.Namespace):
    choice = args.provider or ("mock" if args.mock_response else "openai")
    if choice == "mock":
        if not args.mock_response:
            raise ValueError("mock provider requires at least one --mock-response file; use --provider openai --endpoint URL for a real model")
        return MockProvider(Path(path).read_text() for path in args.mock_response)
    if not args.endpoint:
        raise ValueError("--endpoint or CDAVC_ENDPOINT is required for a real model; pass --provider mock --mock-response FILE to replay a scripted answer instead")
    sampling = SamplingParams(temperature=args.temperature, top_p=args.top_p,
                              top_k=args.top_k, max_tokens=args.max_output_tokens)
    if sampling == SamplingParams():
        sampling = None
    return OpenAICompatibleProvider(
        args.endpoint,
        model=args.model,
        api_key=os.environ.get("CDAVC_API_KEY"),
        timeout=args.timeout,
        sampling=sampling,
    )


def _command(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    parts = tuple(shlex.split(value))
    if not parts:
        raise ValueError("test command cannot be empty")
    return parts


def _progress(message: str) -> None:
    print(f"cdavc: {message}", file=sys.stderr, flush=True)


def _print_patch(result: dict) -> None:
    patch = "".join(task.get("diff", "") for task in result["tasks"].values())
    if patch:
        print(patch, end="" if patch.endswith("\n") else "\n")


def _provider_failure(args: argparse.Namespace, location: str, exc: Exception) -> int:
    """Report an unavailable model once instead of retrying it as a rejected candidate."""
    print(f"cdavc: {location}: {exc}", file=sys.stderr)
    if args.endpoint:
        source = f"the server at {args.endpoint} (model {args.model or 'unset'})"
    else:
        source = "the scripted --mock-response files"
    print(f"cdavc: no repair was attempted: a model that cannot answer is not a rejected candidate; check {source}", file=sys.stderr)
    return 2


def _status(result: dict, location: str, report_dir: Path, *, dry_run: bool) -> int:
    failures = [f"{task_id}: {task.get('failure', 'task failed')}" for task_id, task in result["tasks"].items() if task["status"] != "COMPLETED"]
    if not failures:
        if dry_run:
            print(f"cdavc: dry run: verified, no files written; patch in {report_dir / 'execution_patch.diff'}", file=sys.stderr)
        return 0
    print(f"cdavc: {location}: task run failed ({'; '.join(failures)})", file=sys.stderr)
    print(f"cdavc: report written to {report_dir / 'execution_report.md'}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
