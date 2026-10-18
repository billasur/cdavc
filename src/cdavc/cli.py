"""Command-line entry point for offline and local-provider runs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .providers import MockProvider, OpenAICompatibleProvider
from .supervisor import Supervisor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a CD-AVC task graph")
    parser.add_argument("graph", type=Path, help="path to task_graph.json")
    parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    parser.add_argument("--mock-response", action="append", default=[], help="JSON response file; may be repeated")
    parser.add_argument("--endpoint", default=os.environ.get("CDAVC_ENDPOINT", ""))
    parser.add_argument("--model", default=os.environ.get("CDAVC_MODEL", "local-model"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.provider == "mock":
        if not args.mock_response:
            raise SystemExit("mock provider requires at least one --mock-response file")
        provider = MockProvider(Path(path).read_text() for path in args.mock_response)
    else:
        provider = OpenAICompatibleProvider(args.endpoint, model=args.model, api_key=os.environ.get("CDAVC_API_KEY"))
    result = Supervisor(args.graph, provider).run()
    return 0 if all(task["status"] == "COMPLETED" for task in result["tasks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
