import json
import tempfile
import unittest
from pathlib import Path

from cdavc.providers import MockProvider
from cdavc.supervisor import Supervisor


class SupervisorTests(unittest.TestCase):
    def _project(self, root: Path) -> Path:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "answer.py").write_text("def answer(value: int) -> int:\n    return 0\n")
        (root / "tests" / "test_answer.py").write_text(
            "import unittest\nfrom src.answer import answer\n\n\nclass AnswerTests(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(41), 42)\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
        )
        (root / "task_graph.json").write_text(
            json.dumps({
                "project_id": "demo",
                "tasks": [{
                    "id": "TASK-001",
                    "title": "implement answer",
                    "dependencies": [],
                    "implementation_files": ["src/answer.py"],
                    "test_files": ["tests/test_answer.py"],
                    "symbols": ["answer"],
                    "test_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
                    "max_retries": 1,
                }],
            })
        )
        return root / "task_graph.json"

    def test_supervisor_retries_failed_candidate_and_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return 0\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            result = Supervisor(graph_path, MockProvider([bad, good])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual(result["tasks"]["TASK-001"]["attempts"], 2)
            self.assertTrue((root / "src" / "answer.py").read_text().endswith("return value + 1\n"))
            self.assertTrue((root / "execution_report.md").exists())

    def test_supervisor_rejects_provider_changes_to_test_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"tests/test_answer.py": "broken"}})
            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("allowed implementation", result["tasks"]["TASK-001"]["failure"])

    def test_supervisor_accepts_json_code_fence_from_local_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            response = "```json\n{" + '"files": {"src/answer.py": "def answer(value: int) -> int:\\n    return value + 1\\n"}' + "}\n```"

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")

    def test_supervisor_rejects_missing_declared_test_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["test_files"] = ["tests/missing_test.py"]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("declared test file does not exist", result["tasks"]["TASK-001"]["failure"])

    def test_supervisor_rejects_task_without_declared_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["test_files"] = []
            graph_path.write_text(json.dumps(payload))

            result = Supervisor(graph_path, MockProvider([])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("at least one declared test file", result["tasks"]["TASK-001"]["failure"])

    def test_supervisor_rejects_syntax_error_and_restores_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            original = (root / "src" / "answer.py").read_text()
            response = json.dumps({"files": {"src/answer.py": "def answer(:\n    pass\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("AST gate failed", result["tasks"]["TASK-001"]["failure"])
            self.assertEqual((root / "src" / "answer.py").read_text(), original)

    def test_supervisor_rejects_missing_required_symbol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def other(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("missing symbols", result["tasks"]["TASK-001"]["failure"])
    def test_supervisor_rejects_candidate_that_never_raises_required_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            payload["tasks"][0]["invariants"] = ["Raise ValueError for non-positive input."]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("AST gate failed", result["tasks"]["TASK-001"]["failure"])
            self.assertIn("raising ValueError", result["tasks"]["TASK-001"]["failure"])

    def test_supervisor_accepts_candidate_that_raises_required_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            payload["tasks"][0]["invariants"] = ["Raise ValueError for non-positive input."]
            graph_path.write_text(json.dumps(payload))
            body = (
                "def answer(value: int) -> int:\n"
                "    if value < 0:\n"
                "        raise ValueError('negative input')\n"
                "    return value + 1\n"
            )
            response = json.dumps({"files": {"src/answer.py": body}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
