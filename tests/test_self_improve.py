"""Offline tests for the self-improvement loop. No model calls, no spend."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cdavc.providers import MockProvider  # noqa: E402
from self_improve.config import ConfigError, HarnessConfig, one_knob_mutations  # noqa: E402
from self_improve.controller import (  # noqa: E402
    Controller,
    EvaluatorTamperedError,
    check_evaluator_clean,
    is_better,
)
from self_improve.evaluator import EvalResult, LiveEvaluator, SimulatedEvaluator  # noqa: E402
from self_improve.proposer import ModelProposer, ScriptedProposer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- config surface ---

def test_config_roundtrip():
    c = HarnessConfig(retry_cap=2, prompt_layout="stable-prefix", lenient_parse=False)
    assert HarnessConfig.from_dict(json.loads(c.to_json())) == c
    assert c.to_runner_kwargs() == {
        "retry_cap": 2, "prompt_layout": "stable-prefix", "lenient_parse": False}


def test_config_rejects_unknown_keys():
    with pytest.raises(ConfigError, match="outside editable surface"):
        HarnessConfig.from_dict({"retry_cap": 2, "grading": "lenient"})


@pytest.mark.parametrize("payload", [
    {"retry_cap": -1}, {"retry_cap": 4}, {"retry_cap": True},
    {"prompt_layout": "chaotic"}, {"lenient_parse": "yes"},
])
def test_config_bounds(payload):
    with pytest.raises(ConfigError):
        HarnessConfig.from_dict(payload)


def test_mutations_differ_by_exactly_one_knob():
    base = HarnessConfig()
    for cand in one_knob_mutations(base):
        diffs = [k for k in ("retry_cap", "prompt_layout", "lenient_parse")
                 if getattr(cand, k) != getattr(base, k)]
        assert len(diffs) == 1


# --- proposers ---

def test_scripted_proposer_exhausts():
    tried = [HarnessConfig()]
    seen = 0
    while True:
        nxt = ScriptedProposer().propose(HarnessConfig(), tried, [])
        if nxt is None:
            break
        tried.append(nxt)
        seen += 1
    assert seen == len(one_knob_mutations(HarnessConfig()))


def test_model_proposer_refuses_without_approval():
    with pytest.raises(PermissionError):
        ModelProposer().propose(HarnessConfig(), [], [])


# --- evaluator labels ---

def test_simulated_is_never_a_measurement():
    result = SimulatedEvaluator().evaluate(HarnessConfig())
    assert result.simulated is True
    assert result.tokens is None


def test_is_better_pass_count_then_tokens():
    a = EvalResult(5, 13, 1000, simulated=False)
    b = EvalResult(4, 13, 10, simulated=False)
    assert is_better(a, b)
    assert not is_better(b, a)
    cheaper = EvalResult(5, 13, 900, simulated=False)
    assert is_better(cheaper, a)


# --- controller mechanics in a hermetic git repo ---

def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "self_improve" / "protected").mkdir(parents=True)
    (repo / "benchmarks_dev2").mkdir()
    (repo / "benchmarks_heldout").mkdir()
    (repo / "self_improve" / "protected" / "tasks.json").write_text("{}")
    (repo / "self_improve" / "harness_config.json").write_text(
        HarnessConfig().to_json())
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


class FakeEvaluator:
    """Scripted MEASURED-style scores keyed by config JSON (test double)."""

    def __init__(self, scores: dict[str, EvalResult]):
        self.scores = scores

    def evaluate(self, config: HarnessConfig) -> EvalResult:
        return self.scores[config.to_json().strip()]


def test_controller_keeps_better_and_rolls_back_worse(tmp_path):
    repo = _make_repo(tmp_path)
    incumbent = HarnessConfig()  # retry_cap 3, default, lenient
    better = HarnessConfig(retry_cap=2)
    worse = HarnessConfig(retry_cap=1)
    scores = {
        better.to_json().strip(): EvalResult(9, 13, 5000, simulated=False),
        worse.to_json().strip(): EvalResult(3, 13, 1000, simulated=False),
    }
    # proposer order for base config: retry_cap 0,1,2 ... ; drive it directly
    order = [better, worse]

    class FixedOrder:
        def propose(self, current, tried, history):
            return order.pop(0) if order else None

    state = Controller(repo, FixedOrder(), FakeEvaluator(scores)).run(2)
    assert state.best_config == better
    assert state.best_result and state.best_result.passed == 9
    # config file holds the incumbent (better) config, worse was rolled back
    assert HarnessConfig.load(repo / "self_improve" / "harness_config.json") == better
    log = (repo / "self_improve" / "IMPROVE_LOG.md").read_text()
    assert "KEPT - measured" in log
    assert "rolled back - measured" in log
    commits = subprocess.run(["git", "log", "--oneline"], cwd=repo,
                             capture_output=True, text=True).stdout
    assert commits.count("self-improve: keep") == 1


def test_controller_aborts_on_dirty_evaluator(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "self_improve" / "protected" / "tasks.json").write_text('{"tampered": true}')
    with pytest.raises(EvaluatorTamperedError):
        check_evaluator_clean(repo)
    with pytest.raises(EvaluatorTamperedError):
        Controller(repo, ScriptedProposer(), SimulatedEvaluator()).run(1)


def test_controller_never_keeps_simulated(tmp_path):
    repo = _make_repo(tmp_path)
    original = HarnessConfig()
    state = Controller(repo, ScriptedProposer(), SimulatedEvaluator()).run(3)
    assert state.best_result is None
    assert HarnessConfig.load(repo / "self_improve" / "harness_config.json") == original
    log = (repo / "self_improve" / "IMPROVE_LOG.md").read_text()
    assert "simulated (mechanics only)" in log
    assert "KEPT" not in log


# --- measured path, offline: real benchmark, mock provider, one dev2 task ---

def test_live_evaluator_smoke_with_mock_provider(tmp_path):
    tid = "task_e03_wrap_text"
    task_dir = Path("benchmarks_dev2/agent10") / tid
    reference = (REPO_ROOT / task_dir / "reference_solution.py").read_text()
    response = json.dumps({"files": [ ]})  # placeholder, replaced below
    response = json.dumps({"files": {(task_dir / "solution_stub.py").as_posix(): reference}})
    provider = MockProvider([
        {"text": response, "usage": {"prompt_tokens": 100, "completion_tokens": 50}},
    ])
    evaluator = LiveEvaluator(REPO_ROOT, provider, token_cap=5000,
                              results_dir=tmp_path)
    evaluator.task_ids = [tid]
    result = evaluator.evaluate(HarnessConfig())
    assert result.simulated is False
    assert result.total == 1
    assert result.passed == 1, "reference solution must pass all cdavc gates"
    assert result.tokens == 150
