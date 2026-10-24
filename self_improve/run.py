"""CLI for the self-improvement loop.

Offline mechanics check (no model, no spend, scores are SIMULATED):
    python -m self_improve.run --iterations 3 --evaluator simulated

Live MEASURED run (spends tokens; needs explicit approval and a hard cap):
    CDAVC_API_KEY_FILE=/path/to/key python -m self_improve.run \
        --evaluator live --model openai/gpt-oss-20b \
        --approve-spend --token-cap 15000 --iterations 2 --validate

The key file is read, never printed. --validate re-runs every provisional
keep on extra seeds (see controller.VALIDATION_SEEDS) before it counts as a
validated gain; without it, keeps stay provisional single-seed results.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

GROQ_CHAT_COMPLETIONS = "https://api.groq.com/openai/v1/chat/completions"


def _build_provider(model: str, base_url: str):
    from cdavc.providers import OpenAICompatibleProvider

    key_file = os.environ.get("CDAVC_API_KEY_FILE")
    if not key_file:
        raise SystemExit("CDAVC_API_KEY_FILE is not set; expected a 0600 key file path")
    api_key = Path(key_file).read_text().strip()

    def opener(request):
        # Groq rejects urllib's default User-Agent with HTTP 403.
        request.add_header("User-Agent", "cdavc-self-improve/1.0")
        return urlopen(request, timeout=60)

    return OpenAICompatibleProvider(base_url, model=model, api_key=api_key, opener=opener)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CD-AVC harness self-improvement loop")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--evaluator", choices=("simulated", "live"), default="simulated")
    parser.add_argument("--proposer", choices=("scripted", "model"), default="scripted")
    parser.add_argument("--model", default="openai/gpt-oss-20b",
                        help="model id for live evaluation and/or model proposer")
    parser.add_argument("--base-url", default=GROQ_CHAT_COMPLETIONS)
    parser.add_argument("--token-cap", type=int, default=0,
                        help="required for --evaluator live; TOTAL budget covering "
                             "proposals, evaluations and validation re-runs")
    parser.add_argument("--approve-spend", action="store_true",
                        help="confirms token spend was approved for this run")
    parser.add_argument("--validate", action="store_true",
                        help="re-check every provisional keep on extra seeds before counting it")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent

    needs_model = args.evaluator == "live" or args.proposer == "model"
    if needs_model and (not args.approve_spend or (args.evaluator == "live" and args.token_cap <= 0)):
        print("model use needs --approve-spend (and --token-cap N for live evaluation); "
              "no spend approval is on record by default", file=sys.stderr)
        return 2

    provider = _build_provider(args.model, args.base_url) if needs_model else None

    budget = None
    if args.evaluator == "live" or args.proposer == "model":
        from .budget import Budget
        budget = Budget(args.token_cap or 1)

    if args.proposer == "model":
        from .proposer import ModelProposer
        proposer = ModelProposer(provider, spend_approved=args.approve_spend, budget=budget)
    else:
        from .proposer import ScriptedProposer
        proposer = ScriptedProposer()

    if args.evaluator == "simulated":
        from .evaluator import SimulatedEvaluator
        evaluator = SimulatedEvaluator()
        evaluator_for_seed = None
    else:
        from .evaluator import LiveEvaluator

        def make_eval(seed: int) -> "LiveEvaluator":
            return LiveEvaluator(repo_root, provider, token_cap=args.token_cap,
                                 seed=seed, budget=budget)

        evaluator = make_eval(args.seed)
        evaluator_for_seed = make_eval if args.validate else None

    from .controller import Controller
    controller = Controller(repo_root, proposer, evaluator,
                            evaluator_for_seed=evaluator_for_seed)
    state = controller.run(args.iterations)
    status = "multi-seed observed gain under this protocol" if state.validated else (
        "provisional (single-seed) best" if state.best_result else "no improvement found")
    print(f"done: {len(state.history)} iterations, "
          f"best={state.best_config.to_json().strip()} [{status}]")
    if budget is not None:
        print("budget:", budget.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
