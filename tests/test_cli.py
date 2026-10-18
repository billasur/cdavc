import contextlib
import io
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from cdavc.cli import main


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
