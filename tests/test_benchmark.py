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
    BenchmarkError,
    BenchmarkRunner,
    BenchmarkTask,
    paired_pass_rate_difference,
    render_report,
)
from cdavc.benchmark import main as benchmark_main
from cdavc.providers import MockProvider, OpenAICompatibleProvider, ProviderCompletion


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

    def test_runner_records_three_arms_with_usage_metadata_and_resumes(self):
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

            line_count = len(records_path.read_text().splitlines())
            with patch.object(BenchmarkRunner, "_provider_for", side_effect=AssertionError("resumed")):
                resumed = runner.run()
            self.assertEqual(len(resumed), 3)
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

    def test_baselines_skip_cage_gates_and_cage_uses_a_git_worktree(self):
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

            self.assertEqual(cage_calls, ["answer"])
            self.assertTrue(all(record["pass"] for record in records))
            worktrees = subprocess.run(
                ["git", "worktree", "list"], cwd=root, check=True, text=True, capture_output=True
            ).stdout.splitlines()
            self.assertEqual(len(worktrees), 1)
            self.assertEqual((root / "src" / "answer.py").read_text().strip().splitlines()[-1].strip(), "return 0")

    def test_baselines_are_scored_on_hidden_tests_and_retry_gets_only_failure_output(self):
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
            prompts = {"baseline_single": [], "baseline_retry": [], "cdavc": []}

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
            self.assertIn("hidden assertion failed", prompts["baseline_retry"][1])
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
            self.assertTrue(all(record["attempts"] <= 3 for record in records))
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

    def test_fixed_corpus_has_thirty_unique_tasks_and_separate_hidden_evaluator(self):
        corpus = json.loads(Path("benchmarks/tasks.json").read_text())
        tasks = corpus["tasks"]
        self.assertEqual(len(tasks), 30)
        self.assertEqual(len({task["task_id"] for task in tasks}), 30)
        self.assertEqual(corpus["source"]["kind"], "original")
        for task in tasks:
            self.assertTrue(task["hidden_test_command"])
            self.assertNotIn("hidden_tests.py", task["description"])
            implementation = Path(task["implementation_files"][0])
            self.assertTrue(implementation.is_file())

    def test_report_contains_arm_table_paired_ci_overhead_and_cage_hurt_cases(self):
        records = []
        for task_id, baseline_pass, cdavc_pass in (("a", True, True), ("b", True, False), ("c", False, True)):
            for arm, passed, wall, token_in in (
                ("baseline_single", baseline_pass, 1.0, 10),
                ("baseline_retry", baseline_pass, 1.5, 12),
                ("cdavc", cdavc_pass, 2.0, 15),
            ):
                records.append(
                    {
                        "task_id": task_id,
                        "arm": arm,
                        "pass": passed,
                        "passed": passed,
                        "attempts": 1,
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

    def test_cage_hidden_failure_reports_invariants_without_leaking_assertions(self):
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
            prompts = []

            class SequenceProvider:
                available = True

                def __init__(self):
                    self.responses = iter([candidate, candidate])

                def complete_with_metadata(self, messages, *, seed=None):
                    prompts.append(messages[0]["content"])
                    return next(self.responses)

            def provider_factory(arm, _task):
                return SequenceProvider() if arm == "cdavc" else MockProvider([candidate])

            records = BenchmarkRunner(
                root,
                provider_factory,
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertFalse(cage["pass"])
            self.assertIn("hidden test failed", cage["failure"])
            self.assertIn("hidden test failed", prompts[1])
            self.assertIn("Verification Gate Failed: Invariant check or edge-case boundary violation.", prompts[1])
            self.assertIn("Ensure your implementation satisfies all declared invariants:", prompts[1])
            for invariant in invariants:
                self.assertIn(f"- {invariant}", prompts[1])
            self.assertIn("duplicate values, empty inputs, boundary ranges, and explicit exception raising", prompts[1])
            self.assertNotIn(secret, "\n".join(prompts))

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
            )
            with patch.object(BenchmarkRunner, "_run_command", spy):
                records = runner.run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertFalse(cage["pass"])
            self.assertIn(
                "AST Contract Failed: Task invariant requires input validation raising ValueError, "
                "but no raise of ValueError was found in implementation.",
                cage["failure"],
            )
            self.assertEqual(cage["gate_results"], [])
            self.assertNotIn("targeted test", labels)

    def test_cage_rejects_wrong_exception_class_before_running_public_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task(
                max_retries=0,
                invariants=("Raise ValueError when size is not positive.",),
                regression_command=None,
            )
            candidate = self._response("def answer() -> int:\n    raise TypeError('wrong class')\n")
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
            )
            with patch.object(BenchmarkRunner, "_run_command", spy):
                records = runner.run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertFalse(cage["pass"])
            self.assertIn(
                "AST Contract Failed: Task invariant requires input validation raising ValueError, "
                "but no raise of ValueError was found in implementation.",
                cage["failure"],
            )
            self.assertEqual(cage["gate_results"], [])
            self.assertNotIn("targeted test", labels)

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


if __name__ == "__main__":
    unittest.main()
