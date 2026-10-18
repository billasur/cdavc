"""Command-line entry point for offline and local-provider runs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .providers import MockProvider, OpenAICompatibleProvider, ProviderUnavailableError
from .supervisor import Supervisor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a CD-AVC task graph")
    parser.add_argument("graph", type=Path, help="path to task_graph.json")
    parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    parser.add_argument("--mock-response", action="append", default=[], help="JSON response file; may be repeated")
    parser.add_argument("--endpoint", default=os.environ.get("CDAVC_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("CDAVC_MODEL", "local-model"))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("CDAVC_TIMEOUT", "30")), help="provider request timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    location = str(args.graph)
    try:
        if args.provider == "mock":
            if not args.mock_response:
                raise ValueError("mock provider requires at least one --mock-response file")
            provider = MockProvider(Path(path).read_text() for path in args.mock_response)
        else:
            if not args.endpoint:
                raise ValueError("--endpoint or CDAVC_ENDPOINT is required for --provider openai")
            provider = OpenAICompatibleProvider(
                args.endpoint,
                model=args.model,
                api_key=os.environ.get("CDAVC_API_KEY"),
                timeout=args.timeout,
            )
        result = Supervisor(args.graph, provider).run()
    except (OSError, ProviderUnavailableError, RuntimeError, ValueError) as exc:
        print(f"cdavc: {location}: {exc}", file=sys.stderr)
        return 2
    if all(task["status"] == "COMPLETED" for task in result["tasks"].values()):
        return 0
    failures = [f"{task_id}: {task.get('failure', 'task failed')}" for task_id, task in result["tasks"].items() if task["status"] != "COMPLETED"]
    print(f"cdavc: {location}: task run failed ({'; '.join(failures)})", file=sys.stderr)
    print(f"cdavc: report written to {args.graph.resolve().parent / 'execution_report.md'}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
