import json
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cdavc.benchmark import (
    ARMS,
    CAGE_ARMS,
    MAX_CANDIDATE_CHARS,
    BenchmarkError,
    BenchmarkRunner,
    BenchmarkTask,
    failure_categories,
    paired_pass_rate_difference,
    render_report,
)
from cdavc.benchmark import main as benchmark_main
from cdavc.providers import MockProvider, OpenAICompatibleProvider, ProviderCompletion
from cdavc.accounting import Budget
from cdavc.accounting import UsageLedger


class BenchmarkTests(unittest.TestCase):
    def _git_project(self, root: Path) -> Path:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "answer.py").write_text("def answer() -> int:\n    return 0\n")
        (root / "tests" / "test_answer.py").write_text(
            "import unittest\n"
            "from src.answer import answer\n\n"
            "class AnswerTests(unittest.TestCase):\n"
            "    def test_answer(self):\n"
            "        self.assertEqual(answer(), 42)\n"
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "CD-AVC tests"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
        return root

    def _task(self, *, max_retries: int = 1, **kwargs) -> BenchmarkTask:
        values = {
            "task_id": "answer",
            "title": "Implement the answer function",
            "description": "Return the input value plus one.",
            "source": "test-fixture-v1",
            "implementation_files": ("src/answer.py",),
            "test_files": ("tests/test_answer.py",),
            "symbols": ("answer",),
            "test_command": ("python", "-m", "unittest", "tests.test_answer"),
            "regression_command": ("python", "-m", "unittest", "discover", "-s", "tests"),
            "max_retries": max_retries,
        }
        values.update(kwargs)
        return BenchmarkTask(**values)

    def _response(self, body: str, *, prompt_tokens: int = 7, completion_tokens: int = 5) -> ProviderCompletion:
        return ProviderCompletion(
            text=json.dumps({"files": {"src/answer.py": body}}),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def test_mixed_usage_reask_is_visibly_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            good = self._response("def answer() -> int:\n    return 42\n")
            runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([
                ProviderCompletion("not json", 7, 5), ProviderCompletion(good.text)
            ]), tasks=[self._task(max_retries=0)], records_path=root / "records.jsonl", samples=1)
            for row in runner.run():
                self.assertEqual(row["provider_calls"], 2)
                self.assertEqual(row["token_usage_source"], "provider_partial")
                self.assertFalse(row["usage_complete"])
                self.assertIsNone(row["token_in"])
                self.assertEqual(row["known_token_in"], 7)
                self.assertEqual(row["call_log"][1]["purpose"], "json_reask")

    def test_call_budget_stops_reasks_without_extra_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([
                ProviderCompletion("not json", 7, 5)
            ]), tasks=[self._task()], records_path=root / "records.jsonl", budget=Budget(max_calls=1))
            for row in runner.run():
                self.assertEqual(row["outcome"], "budget_exhausted")
                self.assertEqual(row["provider_calls"], 1)
                self.assertFalse(row["accepted"])

    def test_retries_do_not_inherit_files_created_by_rejected_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            bad = self._response("from pathlib import Path\nPath('poison').write_text('x')\ndef answer(): return 0\n")
            good = self._response("from pathlib import Path\nassert not Path('poison').exists()\ndef answer(): return 42\n")
            runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([bad, good]),
                tasks=[self._task()], records_path=root / "records.jsonl")
            for row in runner.run():
                if row["arm"] != "baseline_single":
                    self.assertTrue(row["pass"], row)
                    self.assertEqual(row["attempts"], 2)

    def test_context_search_is_counted_as_a_call_not_a_draw_or_json_reask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            query = ProviderCompletion(json.dumps({"context_search": "answer"}), 7, 5)
            good = self._response("def answer(): return 42\n")
            runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([query, good]),
                tasks=[self._task(max_retries=0)], records_path=root / "records.jsonl", samples=1)
            for row in runner.run():
                self.assertTrue(row["pass"], row)
                self.assertEqual(row["provider_calls"], 2)
                self.assertEqual(row["attempts"], 1)
                self.assertEqual(row["json_reasks"], 0)
                self.assertEqual(row["call_log"][1]["purpose"], "context_retrieval")

    def test_wall_budget_is_checked_after_public_verification_and_final_scoring(self):
        for stage in ("_run_cage_gates", "_run_final_evaluation"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                root = self._git_project(Path(directory))
                good = self._response("def answer(): return 42\n")
                runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([good]), tasks=[self._task()],
                    records_path=root / "records.jsonl", budget=Budget(max_wall_seconds=1))
                ticks = [0.0]
                ledger = UsageLedger(runner.budget, clock=lambda: ticks[0])
                original = getattr(runner, stage)

                def slow(*args, **kwargs):
                    result = original(*args, **kwargs)
                    ticks[0] = 2.0
                    return result

                with patch("cdavc.benchmark.UsageLedger", return_value=ledger), patch.object(runner, stage, side_effect=slow):
                    row = runner._run_arm(self._task(), "cdavc", runner._lock_test_hashes(self._task()))
                self.assertEqual(row["outcome"], "budget_exhausted")
                self.assertFalse(row["pass"])
                self.assertEqual(row["provider_calls"], 1)

    def test_identical_cli_run_resumes_when_reports_are_outside_results_directory(self):
        for report in (None, "reports/nested/report.md"):
            with self.subTest(report=report), tempfile.TemporaryDirectory() as directory:
                root = self._git_project(Path(directory))
                task = self._task(max_retries=0)
                tasks = root / "tasks.json"
                tasks.write_text(json.dumps([{"task_id": task.task_id, "implementation_files": list(task.implementation_files),
                    "test_files": list(task.test_files), "symbols": list(task.symbols), "test_command": list(task.test_command), "max_retries": 0}]))
                response = root / "response.json"
                response.write_text(self._response("def answer(): return 42\n").text)
                args = [str(root), "--tasks", str(tasks), "--records", str(root / "records.jsonl"),
                        "--mock-response", str(response), "--samples", "1"]
                if report:
                    args += ["--report", report]
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(benchmark_main(args), 0)
                    self.assertEqual(benchmark_main(args), 0)

    def test_resume_rejects_changed_budgets_tasks_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            good = self._response("def answer() -> int:\n    return 42\n")
            factory = lambda _arm, _task: MockProvider([good])
            options = dict(tasks=[task], records_path=root / "records.jsonl", samples=1)
            BenchmarkRunner(root, factory, **options).run()
            for extra in ({"samples": 2}, {"retry_cap": 2}, {"timeout_seconds": 7},
                          {"budget": Budget(max_calls=2)}):
                with self.subTest(extra=extra), self.assertRaisesRegex(BenchmarkError, "fingerprint"):
                    BenchmarkRunner(root, factory, **(options | extra))
            (root / "src/answer.py").write_text("def answer():\n    return 1\n")
            with self.assertRaisesRegex(BenchmarkError, "fingerprint"):
                BenchmarkRunner(root, factory, **options)

    def test_runner_records_every_arm_with_usage_metadata_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            records_path = root / "records.jsonl"
            task = self._task(max_retries=0)
            good = "def answer() -> int:\n    return 42\n"

            def provider_factory(arm, _task):
                return MockProvider([self._response(good)])

            runner = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=records_path,
                seed=17,
                model="local-test",
                quantisation="q4_k_m",
                version="test-version",
                hardware="test-hardware",
            )
            records = runner.run()

            self.assertEqual([record["arm"] for record in records], list(ARMS))
            for record in records:
                self.assertEqual(record["task_id"], "answer")
                self.assertTrue(record["pass"])
                self.assertTrue(record["passed"])
                self.assertEqual(record["attempts"], 1)
                self.assertEqual(record["token_in"], 7)
                self.assertEqual(record["token_out"], 5)
                self.assertIsInstance(record["wall_time_seconds"], float)
                self.assertIsInstance(record["peak_memory_bytes"], int)
                self.assertTrue(record["peak_memory_source"])
                self.assertEqual(record["model"], "local-test")
                self.assertEqual(record["quantisation"], "q4_k_m")
                self.assertEqual(record["version"], "test-version")
                self.assertEqual(record["hardware"], "test-hardware")
                self.assertEqual(record["seed"], 17)
                expected_budget = {
                    "baseline_single": 1,
                    "baseline_retry": 1,
                    "cdavc": 1,
                    "cdavc_sampled": 4,
                    "cdavc_sampled_repair": 4,
                }[record["arm"]]
                self.assertEqual(record["samples_budget"], expected_budget)
                self.assertEqual(record["samples_drawn"], 1)
                self.assertEqual(record["samples_to_accept"], 1)

            line_count = len(records_path.read_text().splitlines())
            with patch.object(BenchmarkRunner, "_provider_for", side_effect=AssertionError("resumed")):
                resumed = runner.run()
            self.assertEqual(len(resumed), len(ARMS))
            self.assertEqual(len(records_path.read_text().splitlines()), line_count)

            (root / "tests" / "test_answer.py").write_text("changed\n")
            with self.assertRaises(BenchmarkError):
                BenchmarkRunner(
                    root,
                    lambda _arm, _task: MockProvider([]),
                    tasks=[task],
                    records_path=records_path,
                ).run()

    def test_resume_rejects_mixed_experiment_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            good = "def answer() -> int:\n    return 42\n"
            records_path = root / "records.jsonl"
            BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([self._response(good)]),
                tasks=[task],
                records_path=records_path,
                seed=11,
                model="model-a",
            ).run()
            with self.assertRaisesRegex(BenchmarkError, "resume metadata mismatch"):
                BenchmarkRunner(
                    root,
                    lambda _arm, _task: MockProvider([self._response(good)]),
                    tasks=[task],
                    records_path=records_path,
                    seed=11,
                    model="model-b",
                )

    def test_baselines_skip_extra_cage_gates_and_source_checkout_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            good = "def answer() -> int:\n    return 42\n"
            runner = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([self._response(good)]),
                tasks=[task],
                records_path=root / "records.jsonl",
            )
            cage_calls = []
            original = runner._run_cage_gates

            def spy(*args, **kwargs):
                cage_calls.append(args[0].task_id)
                return original(*args, **kwargs)

            with patch.object(runner, "_run_cage_gates", side_effect=spy):
                records = runner.run()

            self.assertEqual(cage_calls, ["answer"] * len(CAGE_ARMS))
            self.assertTrue(all(record["pass"] for record in records))
            self.assertTrue(all(record["execution_mode"] == "fresh-snapshot-copy" for record in records))
            worktrees = subprocess.run(
                ["git", "worktree", "list"], cwd=root, check=True, text=True, capture_output=True
            ).stdout.splitlines()
            self.assertEqual(len(worktrees), 1)
            self.assertEqual((root / "src" / "answer.py").read_text().strip().splitlines()[-1].strip(), "return 0")

    def test_baselines_are_scored_on_hidden_tests_but_retry_gets_only_public_failure_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            hidden = root / "hidden_check.py"
            hidden.write_text(
                "from src.answer import answer\n"
                "assert answer() == 42, 'hidden assertion failed'\n"
            )
            subprocess.run(["git", "add", "hidden_check.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "hidden check"], cwd=root, check=True)
            task = self._task(
                max_retries=1,
                test_files=("tests/test_answer.py", "hidden_check.py"),
                hidden_test_command=("python", "hidden_check.py"),
            )
            bad = self._response("def answer() -> int:\n    return 0\n")
            good = self._response("def answer() -> int:\n    return 42\n")
            prompts = {
                "baseline_single": [],
                "baseline_retry": [],
                "cdavc": [],
                "cdavc_sampled": [],
                "cdavc_sampled_repair": [],
            }

            class SequenceProvider:
                available = True

                def __init__(self, responses, arm):
                    self.responses = iter(responses)
                    self.arm = arm

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts[self.arm].append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                if arm == "baseline_single":
                    return SequenceProvider([bad], arm)
                if arm == "baseline_retry":
                    return SequenceProvider([bad, good], arm)
                return SequenceProvider([good], arm)

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            single = next(record for record in records if record["arm"] == "baseline_single")
            retry = next(record for record in records if record["arm"] == "baseline_retry")
            self.assertFalse(single["pass"])
            self.assertTrue(retry["pass"])
            self.assertEqual(retry["attempts"], 2)
            self.assertIn("targeted test failed", prompts["baseline_retry"][1])
            self.assertNotIn("hidden assertion failed", prompts["baseline_retry"][1])
            self.assertNotIn("hidden assertion failed", prompts["baseline_single"][0])

    def test_cage_enforces_ast_hash_hidden_and_regression_gates_without_leaking_hidden_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            secret = "hidden-secret-that-must-not-be-prompted"
            hidden = root / "hidden_check.py"
            hidden.write_text(
                "from src.answer import answer\n"
                f"assert answer() == 42, {secret!r}\n"
            )
            subprocess.run(["git", "add", "hidden_check.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "hidden check"], cwd=root, check=True)
            task = self._task(
                max_retries=1,
                invariants=("return the contract value",),
                hidden_test_command=("python", "hidden_check.py"),
            )
            bad = self._response("def wrong() -> int:\n    return 42\n")
            good = self._response("def answer() -> int:\n    return 42\n")
            prompts = []

            class SequenceProvider:
                available = True

                def __init__(self):
                    self.responses = iter([bad, good])

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts.append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                return SequenceProvider() if arm == "cdavc" else MockProvider([good])

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
                seed=5,
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"])
            self.assertEqual(cage["attempts"], 2)
            self.assertNotIn(secret, "\n".join(prompts))
            self.assertIn("locked_test_hashes", cage)
            self.assertIn("tests/test_answer.py", cage["locked_test_hashes"])

    def test_bounded_retries_and_unavailable_usage_are_recorded_as_null(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=5)

            class AlwaysFail:
                available = True

                def complete(self, _messages):
                    raise RuntimeError("provider failed")

            records = BenchmarkRunner(
                root,
                lambda _arm, _task: AlwaysFail(),
                tasks=[task],
                records_path=root / "records.jsonl",
                retry_cap=2,
            ).run()
            self.assertTrue(all(not record["pass"] for record in records))
            # baseline_single draws once, retry/cdavc are bounded by retry_cap, and
            # the sampled arms spend their own independent draw budget.
            self.assertEqual(
                {record["arm"]: record["attempts"] for record in records},
                {
                    "baseline_single": 1,
                    "baseline_retry": 3,
                    "cdavc": 3,
                    "cdavc_sampled": 4,
                    "cdavc_sampled_repair": 4,
                },
            )
            self.assertTrue(all(record["token_in"] is None and record["token_out"] is None for record in records))

    def test_local_only_provider_rejects_remote_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            provider = OpenAICompatibleProvider("https://remote.example/v1/chat/completions")
            with self.assertRaises(BenchmarkError):
                BenchmarkRunner(
                    root,
                    provider,
                    tasks=[self._task()],
                    records_path=root / "records.jsonl",
                ).run()

    def test_openai_metadata_extension_preserves_usage_and_seed(self):
        captured = {}

        def opener(request, *, timeout):
            captured["payload"] = json.loads(request.data)

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return json.dumps(
                        {
                            "model": "local",
                            "choices": [{"message": {"content": "ok"}}],
                            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
                        }
                    ).encode()

            return Response()

        completion = OpenAICompatibleProvider("http://127.0.0.1:8080/v1/chat/completions", opener=opener).complete_with_metadata(
            [{"role": "user", "content": "hi"}], seed=19
        )
        self.assertEqual((completion.prompt_tokens, completion.completion_tokens), (3, 4))
        self.assertEqual(captured["payload"]["seed"], 19)

    def test_cli_mock_without_response_files_is_deterministic_and_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            (root / "src" / "answer.py").write_text("def answer() -> int:\n    return 42\n")
            subprocess.run(["git", "add", "src/answer.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "good answer"], cwd=root, check=True)
            tasks = root / "tasks.json"
            tasks.write_text(json.dumps({"tasks": [self._task(max_retries=0).__dict__]}))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = benchmark_main([str(root), "--tasks", str(tasks), "--mock"])
            self.assertEqual(status, 0)
            self.assertIn("baseline_single", stdout.getvalue())
            self.assertTrue((root / "results" / "benchmark.jsonl").exists())
            self.assertTrue((root / "results" / "REPORT.md").exists())

    def test_fixed_corpus_has_fifty_unique_tasks_and_separate_hidden_evaluator(self):
        corpus = json.loads(Path("benchmarks/tasks.json").read_text())
        tasks = corpus["tasks"]
        self.assertEqual(len(tasks), 50)
        self.assertEqual(len({task["task_id"] for task in tasks}), 50)
        self.assertEqual(corpus["source"]["kind"], "original")
        for task in tasks:
            self.assertTrue(task["hidden_test_command"])
            self.assertNotIn("hidden_tests.py", task["description"])
            implementation = Path(task["implementation_files"][0])
            self.assertTrue(implementation.is_file())

    def test_report_contains_arm_table_paired_ci_overhead_and_cage_hurt_cases(self):
        records = []
        for task_id, baseline_pass, cdavc_pass in (("a", True, True), ("b", True, False), ("c", False, True)):
            for arm, passed, wall, token_in, drawn in (
                ("baseline_single", baseline_pass, 1.0, 10, 1),
                ("baseline_retry", baseline_pass, 1.5, 12, 2),
                ("cdavc", cdavc_pass, 2.0, 15, 2),
                ("cdavc_sampled", cdavc_pass, 3.0, 24, 3),
            ):
                records.append(
                    {
                        "task_id": task_id,
                        "arm": arm,
                        "pass": passed,
                        "passed": passed,
                        "attempts": drawn,
                        "samples_budget": 4,
                        "samples_drawn": drawn,
                        "samples_to_accept": 1 if passed else None,
                        "json_reasks": 0,
                        "verifier_gap": False,
                        "wall_time_seconds": wall,
                        "token_in": token_in,
                        "token_out": token_in // 2,
                        "peak_memory_bytes": 100,
                        "peak_memory_source": "test",
                        "model": "mock",
                        "quantisation": None,
                        "version": "test",
                        "hardware": "test",
                        "seed": 0,
                    }
                )

        difference = paired_pass_rate_difference(records, "cdavc", "baseline_single")
        self.assertEqual(difference["n"], 3)
        self.assertAlmostEqual(difference["difference"], 0.0)
        report = render_report(records)
        self.assertIn("baseline_single", report)
        self.assertIn("95% CI", report)
        self.assertIn("time overhead", report.lower())
        self.assertIn("token overhead", report.lower())
        self.assertIn("b", report)
        self.assertIn("cage-hurt", report.lower())
        self.assertIn("Measured result", report)
        self.assertIn("`cdavc_sampled`", report)
        self.assertIn("Sampling budget", report)
        self.assertIn("Measured verifier gap", report)
        self.assertIn("Fairness disclosure", report)
        self.assertIn("Measured failure categories", report)

    def test_report_discloses_mixed_runner_versions(self):
        records = [
            {"task_id": "a", "arm": "baseline_single", "pass": True, "runner_version": "2"},
            {"task_id": "a", "arm": "cdavc", "pass": False, "runner_version": "3"},
        ]
        report = render_report(records)
        self.assertIn("## Record provenance", report)
        self.assertIn("| `2` | 1 |", report)
        self.assertIn("| `3` | 1 |", report)
        self.assertNotIn("## Record provenance", render_report(records[:1]))

    def test_failure_categories_count_final_failures_per_arm_in_frequency_order(self):
        records = [
            {"task_id": "a", "arm": "cdavc", "pass": False, "failure": "hidden test failed: expected 3"},
            {"task_id": "b", "arm": "cdavc", "pass": False, "failure": "hidden test failed: expected 4"},
            {"task_id": "c", "arm": "cdavc", "pass": False, "failure": "public test failed: boom"},
            {"task_id": "d", "arm": "baseline_single", "pass": False, "failure": "provider unavailable"},
            {"task_id": "e", "arm": "baseline_single", "pass": True, "failure": ""},
            {"task_id": "f", "arm": "not_an_arm", "pass": False, "failure": "hidden test failed"},
            {"task_id": "g", "arm": "baseline_retry", "pass": False, "failure": "AST contract failed: unparsable"},
            {"task_id": "h", "arm": "baseline_retry", "pass": False, "failure": "AST Contract Failed: missing raise"},
        ]
        categories = failure_categories(records)
        self.assertEqual(
            categories,
            {
                "hidden test failed": {"cdavc": 2},
                "provider unavailable": {"baseline_single": 1},
                "public test failed": {"cdavc": 1},
                "AST contract failed": {"baseline_retry": 2},
            },
        )

    def test_cage_forwards_public_test_traceback_with_sanitised_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=1)
            bad = self._response("def answer() -> int:\n    return 0\n")
            good = self._response("def answer() -> int:\n    return 42\n")
            prompts = []

            class SequenceProvider:
                available = True

                def __init__(self):
                    self.responses = iter([bad, good])

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts.append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                return SequenceProvider() if arm == "cdavc" else MockProvider([good])

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"])
            self.assertEqual(cage["attempts"], 2)
            self.assertIn("targeted test failed", prompts[1])
            self.assertIn("AssertionError: 0 != 42", prompts[1])
            self.assertIn("$WORKSPACE", prompts[1])
            self.assertNotIn(str(root), prompts[1])

    def test_hidden_failure_never_requests_another_candidate_in_any_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            secret = "hidden-secret-that-must-not-be-prompted"
            hidden = root / "hidden_check.py"
            hidden.write_text(
                "from src.answer import answer\n"
                f"assert answer() == 7, {secret!r}\n"
            )
            subprocess.run(["git", "add", "hidden_check.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "hidden check"], cwd=root, check=True)
            invariants = (
                "Preserve duplicate values when merging two sorted lists.",
                "Return an empty list when either input is empty.",
            )
            task = self._task(
                max_retries=1,
                invariants=invariants,
                test_files=("tests/test_answer.py", "hidden_check.py"),
                hidden_test_command=("python", "hidden_check.py"),
            )
            candidate = self._response("def answer() -> int:\n    return 42\n")
            prompts = {arm: [] for arm in ARMS}

            class SequenceProvider:
                available = True

                def __init__(self, arm):
                    self.arm = arm
                    self.responses = iter([candidate, candidate])

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts[self.arm].append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                return SequenceProvider(arm)

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            for record in records:
                self.assertTrue(record["accepted"], record)
                self.assertFalse(record["heldout_pass"], record)
                self.assertFalse(record["pass"])
                self.assertEqual(record["attempts"], 1)
                self.assertEqual(record["attempt_log"][0]["status"], "ACCEPTED")
                self.assertIn("hidden test failed", record["failure"])
                self.assertNotIn("hidden_test", record["gate_results"])
                self.assertEqual(len(prompts[record["arm"]]), 1)
                self.assertNotIn(secret, "\n".join(prompts[record["arm"]]))

    def test_first_draw_prompt_is_identical_across_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task()
            runner = BenchmarkRunner(root, MockProvider([]), tasks=[task], records_path=root / "records.jsonl")
            self.assertEqual(len({runner._prompt(task, arm, "") for arm in ARMS}), 1)

    def test_cage_rejects_missing_required_exception_before_running_public_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(
                max_retries=0,
                invariants=("Raise ValueError when size is not positive.",),
                regression_command=None,
            )
            candidate = self._response("def answer() -> int:\n    return 42\n")
            labels = []
            original = BenchmarkRunner._run_command

            def spy(runner, command, workspace, label, *, include_output=False):
                labels.append(label)
                return original(runner, command, workspace, label, include_output=include_output)

            runner = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([candidate]),
                tasks=[task],
                records_path=root / "records.jsonl",
                samples=1,
            )
            hashes = runner._lock_test_hashes(task)
            for arm in CAGE_ARMS:
                with self.subTest(arm=arm):
                    labels.clear()
                    # Observe one cage arm at a time: baseline public checks
                    # are intentional and must not affect this ordering test.
                    with patch.object(BenchmarkRunner, "_run_command", spy):
                        cage = runner._run_arm(task, arm, hashes)
                    self.assertFalse(cage["pass"])
                    self.assertFalse(cage["accepted"])
                    self.assertIsNone(cage["heldout_pass"])
                    self.assertIn(
                        "AST Contract Failed: Task invariant requires input validation raising ValueError, "
                        "but no Raise statements were found in implementation.",
                        cage["failure"],
                    )
                    self.assertEqual(cage["gate_results"], [])
                    self.assertEqual(labels, [])

    def test_cage_boundary_probe_catches_empty_input_crash_when_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0, boundary_probe=True, regression_command=None)
            self.assertFalse(self._task(max_retries=0).boundary_probe)
            candidate = self._response("def answer(value=0) -> int:\n    return value[0]\n")

            records = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([candidate]),
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertFalse(cage["pass"])
            self.assertIn("boundary probe failed", cage["failure"])
            self.assertIn("IndexError", cage["failure"])
            self.assertNotIn("targeted test", cage["failure"])

    def test_draw_seeds_are_independent_and_paired_across_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            runner = BenchmarkRunner(
                root,
                MockProvider([]),
                tasks=[task],
                records_path=root / "records.jsonl",
                seed=99,
            )
            seeds = [runner._draw_seed(task.task_id, draw) for draw in range(1, 5)]
            self.assertEqual(len(set(seeds)), 4)
            self.assertTrue(all(0 <= seed < 2**31 - 1 for seed in seeds))

            # Draw 1 is identical for every arm, so the arms stay paired; the
            # run seed still changes the stream.
            self.assertIn(
                f"Deterministic seed: {seeds[0]}.", runner._prompt(task, "baseline_single", "", draw=1)
            )
            self.assertIn(f"Deterministic seed: {seeds[0]}.", runner._prompt(task, "cdavc", "", draw=1))
            self.assertIn(f"Deterministic seed: {seeds[1]}.", runner._prompt(task, "cdavc", "", draw=2))
            self.assertIn("standard library only", runner._prompt(task, "cdavc", "", draw=1))

            other = BenchmarkRunner(
                root,
                MockProvider([]),
                tasks=[task],
                records_path=root / "other.jsonl",
                seed=100,
            )
            self.assertNotEqual(other._draw_seed(task.task_id, 1), seeds[0])

    def test_sampled_arm_draws_independently_and_stops_at_first_accepted_draw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=1)
            good = self._response("def answer() -> int:\n    return 42\n")
            providers = {}

            class SequenceProvider:
                available = True

                def __init__(self, responses):
                    self.responses = iter(responses)
                    self.calls = []

                def complete_with_metadata(self, messages, *, seed=None):
                    self.calls.append((messages[0]["content"], seed))
                    return next(self.responses)

            def provider_factory(arm, _task):
                if arm == "cdavc_sampled":
                    provider = SequenceProvider(
                        [
                            self._response("def answer() -> int:\n    return 1\n"),
                            self._response("def answer() -> int:\n    return 2\n"),
                            good,
                        ]
                    )
                else:
                    provider = SequenceProvider([good])
                providers[arm] = provider
                return provider

            runner = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
                seed=23,
                samples=4,
            )
            records = runner.run()
            sampled = next(record for record in records if record["arm"] == "cdavc_sampled")
            self.assertTrue(sampled["pass"])
            self.assertEqual(sampled["samples_budget"], 4)
            self.assertEqual(sampled["samples_drawn"], 3)
            self.assertEqual(sampled["samples_to_accept"], 3)
            self.assertEqual([entry["draw"] for entry in sampled["attempt_log"]], [1, 2, 3])
            calls = providers["cdavc_sampled"].calls
            self.assertEqual(len(calls), 3)
            self.assertEqual([seed for _, seed in calls], [runner._draw_seed(task.task_id, draw) for draw in (1, 2, 3)])
            self.assertEqual(len({seed for _, seed in calls}), 3)
            for prompt, _seed in calls:
                self.assertNotIn("Previous deterministic failure category", prompt)
                self.assertNotIn("Previous candidate", prompt)

    def test_sampled_repair_arm_carries_public_failure_within_the_draw_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=1)
            good = self._response("def answer() -> int:\n    return 42\n")
            providers = {}

            class SequenceProvider:
                available = True

                def __init__(self, responses):
                    self.responses = iter(responses)
                    self.calls = []

                def complete_with_metadata(self, messages, *, seed=None):
                    self.calls.append((messages[0]["content"], seed))
                    return next(self.responses)

            def provider_factory(arm, _task):
                if arm == "cdavc_sampled_repair":
                    provider = SequenceProvider(
                        [
                            self._response("def answer() -> int:\n    return 1\n"),
                            self._response("def answer() -> int:\n    return 2\n"),
                            good,
                        ]
                    )
                else:
                    provider = SequenceProvider([good])
                providers[arm] = provider
                return provider

            runner = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
                seed=23,
                samples=4,
            )
            records = runner.run()
            repair = next(record for record in records if record["arm"] == "cdavc_sampled_repair")
            self.assertTrue(repair["pass"])
            self.assertEqual(repair["samples_budget"], 4)
            self.assertEqual(repair["samples_drawn"], 3)
            self.assertEqual([entry["draw"] for entry in repair["attempt_log"]], [1, 2, 3])
            calls = providers["cdavc_sampled_repair"].calls
            self.assertNotIn("Previous deterministic failure category", calls[0][0])
            for prompt, _seed in calls[1:]:
                self.assertIn("Previous deterministic failure category: targeted test failed", prompt)
                self.assertIn("Public gate output:", prompt)
                self.assertIn("Previous candidate, which failed the gates below", prompt)
            self.assertIn("return 1", calls[1][0])
            self.assertIn("return 2", calls[2][0])
            self.assertEqual([seed for _, seed in calls], [runner._draw_seed(task.task_id, draw) for draw in (1, 2, 3)])
            self.assertEqual(len({seed for _, seed in calls}), 3)

    def test_repair_prompt_quotes_the_previous_candidate_for_every_repair_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=1)
            runner = BenchmarkRunner(
                root,
                MockProvider([]),
                tasks=[task],
                records_path=root / "records.jsonl",
            )
            candidate = "--- src/answer.py ---\ndef answer() -> int:\n    return 1"
            for arm in ("baseline_retry", "cdavc", "cdavc_sampled_repair"):
                prompt = runner._prompt(
                    task,
                    arm,
                    "targeted test failed: expected 42",
                    draw=2,
                    candidate=candidate,
                )
                self.assertIn("Previous candidate, which failed the gates below", prompt)
                self.assertIn("return 1", prompt)
                self.assertIn("targeted test failed", prompt)
            independent = runner._prompt(task, "cdavc", "", draw=1, candidate="")
            self.assertNotIn("Previous candidate", independent)

    def test_candidate_context_quotes_only_changed_files_and_truncates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=1)
            original = {"src/answer.py": (root / "src" / "answer.py").read_text()}
            runner = BenchmarkRunner(
                root,
                MockProvider([]),
                tasks=[task],
                records_path=root / "records.jsonl",
            )
            self.assertEqual(runner._candidate_context(task, root, original), "")

            (root / "src" / "answer.py").write_text("def answer() -> int:\n    return 1\n")
            context = runner._candidate_context(task, root, original)
            self.assertIn("--- src/answer.py ---", context)
            self.assertIn("return 1", context)

            (root / "src" / "answer.py").write_text("x" * (MAX_CANDIDATE_CHARS + 50))
            truncated = runner._candidate_context(task, root, original)
            self.assertIn(f"truncated after {MAX_CANDIDATE_CHARS} characters", truncated)
            self.assertLess(len(truncated), MAX_CANDIDATE_CHARS + 200)

    def test_gate_commands_never_reuse_stale_bytecode(self):
        # A same-size rewrite inside one second would otherwise grade the previous import.
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            runner = BenchmarkRunner(
                root,
                MockProvider([]),
                tasks=[self._task()],
                records_path=root / "records.jsonl",
            )
            probe = "import os, sys\nsys.exit(0 if os.environ.get('PYTHONDONTWRITEBYTECODE') == '1' else 3)\n"
            runner._run_command(("python", "-c", probe), root, "targeted test")

    def test_json_reask_costs_tokens_but_not_a_draw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            good = self._response("def answer() -> int:\n    return 42\n")
            prompts = []

            class SequenceProvider:
                available = True

                def __init__(self):
                    self.responses = iter(
                        [ProviderCompletion("I will implement it in prose.", 7, 5), good]
                    )

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts.append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                return SequenceProvider() if arm == "cdavc" else MockProvider([good])

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"])
            self.assertEqual(cage["attempts"], 1)
            self.assertEqual(cage["samples_drawn"], 1)
            self.assertEqual(cage["json_reasks"], 1)
            self.assertEqual(cage["attempt_log"][0]["json_reasks"], 1)
            self.assertEqual(cage["token_in"], 14)
            self.assertEqual(cage["token_out"], 10)
            self.assertIn("could not be parsed as the required JSON object", prompts[1])

    def test_unescaped_quotes_in_candidate_code_are_applied_without_a_reask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(max_retries=0)
            reply = '''{"files": {"src/answer.py": "def answer() -> int:
    text = "42"
    return int(text)
"}}'''

            def provider_factory(arm, _task):
                if arm == "cdavc":
                    return MockProvider([ProviderCompletion(reply, 7, 5)])
                return MockProvider([self._response("def answer() -> int:\n    return 42\n")])

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"])
            self.assertEqual(cage["attempts"], 1)
            self.assertEqual(cage["json_reasks"], 0)

    def test_multi_file_ast_contract_aggregates_symbols_and_raise_statements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            (root / "src" / "helper.py").write_text("def helper(value: int) -> int:\n    return value\n")
            subprocess.run(["git", "add", "src/helper.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "helper module"], cwd=root, check=True)
            task = self._task(
                max_retries=0,
                implementation_files=("src/answer.py", "src/helper.py"),
                symbols=("answer", "helper"),
                invariants=("Raise ValueError when value is negative.",),
                regression_command=None,
            )
            candidate = ProviderCompletion(
                text=json.dumps(
                    {
                        "files": {
                            "src/answer.py": "def answer() -> int:\n    return 42\n",
                            "src/helper.py": (
                                "def helper(value: int) -> int:\n"
                                "    if value < 0:\n"
                                "        raise ValueError('value must be non-negative')\n"
                                "    return value\n"
                            ),
                        }
                    }
                )
            )

            records = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([candidate]),
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"], cage["failure"])
            self.assertIn("ast_contract", cage["gate_results"])
            self.assertEqual(cage["ast_contract"]["files"], ["src/answer.py", "src/helper.py"])


if __name__ == "__main__":
    unittest.main()
