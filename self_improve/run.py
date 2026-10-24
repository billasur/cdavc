"""CLI for the self-improvement loop.

Offline mechanics check (no model, no spend, scores are SIMULATED):
    python -m self_improve.run --iterations 3 --evaluator simulated

Live run (MEASURED; spends tokens, needs explicit approval and a cap):
    python -m self_improve.run --iterations 2 --evaluator live --token-cap 15000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .controller import Controller
from .evaluator import LiveEvaluator, SimulatedEvaluator
from .proposer import ScriptedProposer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CD-AVC harness self-improvement loop")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--evaluator", choices=("simulated", "live"), default="simulated")
    parser.add_argument("--token-cap", type=int, default=0,
                        help="required for --evaluator live; hard token budget")
    parser.add_argument("--approve-spend", action="store_true",
                        help="confirms token spend was approved for this run")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    proposer = ScriptedProposer()
    if args.evaluator == "simulated":
        evaluator = SimulatedEvaluator()
    else:
        if not args.approve_spend or args.token_cap <= 0:
            print("live evaluation needs --approve-spend AND --token-cap N; "
                  "no spend approval is on record by default", file=sys.stderr)
            return 2
        print("live evaluator wiring requires a provider; not run without a key",
              file=sys.stderr)
        return 2
    controller = Controller(repo_root, proposer, evaluator)
    state = controller.run(args.iterations)
    print(f"done: {len(state.history)} iterations, "
          f"best={state.best_config.to_json().strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
