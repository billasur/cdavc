import contextlib
import io
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from cdavc.cli import main
from cdavc.providers import OpenAICompatibleProvider, ProviderUnavailableError


class CliTests(unittest.TestCase):
    def test_audit_fixture_cli_writes_measured_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main(["audit-fixtures", "--fixtures", "benchmarks/verifier_fixtures.json", "--output", str(output)])
            self.assertEqual(status, 0)
            report = json.loads(output.read_text())
            self.assertTrue(report["acceptance_criterion_met"])
            self.assertIn("not held-out", output.with_suffix(".md").read_text())

    def test_missing_graph_reports_location_without_traceback(self):
        missing = Path(tempfile.gettempdir()) / "cdavc-missing-task-graph.json"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = main([str(missing), "--mock-response", str(missing)])

        output = stderr.getvalue()
        self.assertNotEqual(status, 0)
        self.assertIn(str(missing), output)
        self.assertIn("No such file", output)
        self.assertNotIn("Traceback", output)

    def test_openai_provider_requires_endpoint(self):
        missing = Path(tempfile.gettempdir()) / "cdavc-missing-endpoint-graph.json"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = main([str(missing), "--provider", "openai"])

        self.assertEqual(status, 2)
        self.assertIn("--endpoint", stderr.getvalue())

    def test_mock_provider_requires_response_file(self):
        missing = Path(tempfile.gettempdir()) / "cdavc-no-response-graph.json"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = main([str(missing)])

        self.assertEqual(status, 2)
        self.assertIn("mock provider requires", stderr.getvalue())

    def test_failed_task_reports_failure_and_report_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "answer.py").write_text("def answer():\n    return 0\n")
            (root / "tests" / "test_answer.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_fail(self): self.assertEqual(1, 2)\n")
            graph = root / "task_graph.json"
            graph.write_text(json.dumps({"project_id": "x", "tasks": [{"id": "A", "title": "a", "implementation_files": ["src/answer.py"], "test_files": ["tests/test_answer.py"], "symbols": ["answer"], "max_retries": 0}]}))
            response = root / "response.json"
            response.write_text(json.dumps({"files": {"src/answer.py": "def answer():\n    return 1\n"}}))
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                status = main([str(graph), "--mock-response", str(response)])

            self.assertEqual(status, 1)
            self.assertIn("task run failed", stderr.getvalue())
            self.assertIn("execution_report.md", stderr.getvalue())

    @patch("cdavc.cli.Supervisor")
    def test_openai_success_returns_zero(self, supervisor_class):
        graph = Path(tempfile.gettempdir()) / "cdavc-openai-success-graph.json"
        supervisor_class.return_value.run.return_value = {"tasks": {"A": {"status": "COMPLETED"}}}

        status = main([str(graph), "--provider", "openai", "--endpoint", "http://127.0.0.1:1", "--timeout", "1"])

        self.assertEqual(status, 0)
        supervisor_class.assert_called_once()


class RunCommandTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "answer.py").write_text("def answer(value: int) -> int:\n    return 0\n")
        (root / "tests" / "test_answer.py").write_text(
            "import unittest\nfrom src.answer import answer\n\n\nclass AnswerTests(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(41), 42)\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
        )

    def _export(self, root):
        self._project(root)
        contract = root / "contract.json"
        contract.write_text(json.dumps({"implementation_files": ["src/answer.py"],
            "test_files": ["tests/test_answer.py"], "symbols": ["answer"],
            "test_command": ["python", "-m", "unittest", "discover", "-s", "tests"]}))
        candidate = root / "candidate.json"
        candidate.write_text(json.dumps({"files": {"src/answer.py": "def answer(value): return value + 1\n"}}))
        return contract, candidate

    def test_verify_export_uses_no_provider_and_never_publishes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, candidate = self._export(root)
            output = root / "results/verification.json"
            with patch("cdavc.cli._provider", side_effect=AssertionError("unexpected generation")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main(["verify", "--contract", str(contract), "--candidate", str(candidate),
                               "--source", "claude", "--directory", str(root), "--output", str(output)])
            self.assertEqual(status, 0)
            report = json.loads(output.read_text())
            self.assertTrue(report["accepted"])
            self.assertIsNone(report["provider_calls"])
            self.assertEqual(report["verification_model_calls"], 0)
            self.assertIn("return 0", (root / "src/answer.py").read_text())

    def test_compare_missing_usage_is_explicitly_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._export(root)
            manifest = root / "comparison.json"
            manifest.write_text(json.dumps({"directory": ".", "contract": "contract.json",
                "budget": {"max_calls": 2, "max_tokens": 100}, "candidates": [
                    {"id": source, "source": source, "candidate": "candidate.json"} for source in ("claude", "codex")]}))
            output = root / "results/comparison.json"
            with patch("cdavc.cli._provider", side_effect=AssertionError("unexpected generation")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main(["compare", "--manifest", str(manifest), "--output", str(output)])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(output.read_text())["comparison_status"], "inconclusive")
            self.assertIn("unknown", output.with_suffix(".md").read_text())

    def test_run_verifies_the_change_and_writes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            response = root / "response.json"
            response.write_text(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}}))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                    "--provider", "mock", "--mock-response", str(response),
                ])

            self.assertEqual(status, 0)
            self.assertEqual((root / "src" / "answer.py").read_text(), "def answer(value: int) -> int:\n    return value + 1\n")
            self.assertIn("+    return value + 1", stdout.getvalue())

    def test_run_dry_run_reports_the_patch_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            response = root / "response.json"
            response.write_text(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}}))
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                    "--dry-run",
                    "--provider", "mock", "--mock-response", str(response),
                ])

            self.assertEqual(status, 0)
            self.assertEqual((root / "src" / "answer.py").read_text(), "def answer(value: int) -> int:\n    return 0\n")
            self.assertIn("dry run", stderr.getvalue())

    def test_run_replays_a_mock_response_without_naming_a_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            response = root / "response.json"
            response.write_text(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}}))

            with patch.dict("os.environ", {"CDAVC_ENDPOINT": ""}), contextlib.redirect_stdout(io.StringIO()):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                    "--mock-response", str(response),
                ])

            self.assertEqual(status, 0)
            self.assertEqual((root / "src" / "answer.py").read_text(), "def answer(value: int) -> int:\n    return value + 1\n")

    def test_run_samples_another_candidate_when_the_first_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            bad = root / "bad.json"
            bad.write_text(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value\n"}}))
            good = root / "good.json"
            good.write_text(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}}))

            with contextlib.redirect_stdout(io.StringIO()):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                    "--max-retries", "0",
                    "--samples", "2",
                    "--mock-response", str(bad), "--mock-response", str(good),
                ])

            self.assertEqual(status, 0)
            self.assertEqual((root / "src" / "answer.py").read_text(), "def answer(value: int) -> int:\n    return value + 1\n")

    def test_run_call_budget_counts_context_retrieval_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            response = root / "request.json"
            response.write_text(json.dumps({"context_search": "answer"}))
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                status = main(["run", "increment", "--file", "src/answer.py", "--test", "tests/test_answer.py",
                    "--directory", str(root), "--mock-response", str(response), "--max-calls", "1"])
            self.assertEqual(status, 1)
            row = json.loads((root / "execution_log.json").read_text())["tasks"]["T1"]
            self.assertEqual(row["outcome"], "budget_exhausted")
            self.assertEqual(row["accounting"]["calls"], 1)
            self.assertIn("return 0", (root / "src/answer.py").read_text())

    def test_run_checks_executable_properties_not_just_a_raise_statement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            response = root / "candidate.json"
            response.write_text(json.dumps({"files": {"src/answer.py":
                "def answer(value):\n    if False: raise ValueError()\n    return value + 1\n"}}))
            cases = root / "properties.json"
            cases.write_text(json.dumps([{"name": "invalid value", "file": "src/answer.py", "symbol": "answer",
                                         "args": [-1], "raises": "ValueError"}]))
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                status = main(["run", "increment", "--file", "src/answer.py", "--test", "tests/test_answer.py",
                    "--directory", str(root), "--mock-response", str(response), "--max-retries", "0",
                    "--property-file", str(cases), "--check-repeats", "2"])
            self.assertEqual(status, 1)
            row = json.loads((root / "execution_log.json").read_text())["tasks"]["T1"]
            self.assertIn("expected exception was not raised", row["failure"])
            self.assertIn("return 0", (root / "src/answer.py").read_text())

    def test_run_requires_a_test_file_that_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_missing.py",
                    "--directory", str(root),
                    "--provider", "mock", "--mock-response", str(root / "unused.json"),
                ])

            self.assertEqual(status, 2)
            self.assertIn("declared test file does not exist", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_a_dead_model_server_is_reported_once_without_retrying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            endpoint = "http://127.0.0.1:9/v1/chat/completions"
            stderr = io.StringIO()
            calls = []

            def unavailable(request, *, timeout=None):
                calls.append(request)
                raise OSError("connection refused")

            provider = OpenAICompatibleProvider(endpoint, model="local-test", opener=unavailable)

            with patch("cdavc.cli.OpenAICompatibleProvider", return_value=provider), contextlib.redirect_stderr(stderr):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                    "--endpoint", endpoint,
                ])

            output = stderr.getvalue()
            self.assertEqual(status, 2)
            self.assertEqual(len(calls), 1)
            self.assertIn("no repair was attempted", output)
            self.assertIn(endpoint, output)
            self.assertNotIn("Traceback", output)

    def test_run_explains_a_missing_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            stderr = io.StringIO()

            with patch.dict("os.environ", {"CDAVC_ENDPOINT": ""}), contextlib.redirect_stderr(stderr):
                status = main([
                    "run", "make answer increment",
                    "--file", "src/answer.py",
                    "--test", "tests/test_answer.py",
                    "--directory", str(root),
                ])

            self.assertEqual(status, 2)
            self.assertIn("--endpoint", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
