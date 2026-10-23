import json
import tempfile
import unittest
from pathlib import Path

from cdavc.providers import MockProvider, ProviderUnavailableError
from cdavc.supervisor import Supervisor


class _UnavailableProvider:
    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return False

    def complete(self, messages) -> str:
        self.calls += 1
        raise ProviderUnavailableError("provider request failed: connection refused")


class _CapturingProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def available(self) -> bool:
        return True

    def complete(self, messages) -> str:
        self.prompts.extend(message["content"] for message in messages)
        return self.response


class _SequenceProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def available(self) -> bool:
        return True

    def complete(self, messages) -> str:
        self.prompts.append(messages[-1]["content"])
        return self.responses.pop(0)


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
            self.assertIn("Provider calls", (root / "execution_report.md").read_text())
            self.assertIn("incomplete", (root / "execution_report.md").read_text())

    def test_samples_raise_the_draw_budget_and_carry_the_failure_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return 0\n"}})
            # A byte-identical repeat of a rejected reply is stagnation and stops the
            # run early, so the second rejected draw must differ from the first.
            also_bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return -1\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            provider = _SequenceProvider([bad, also_bad, good])

            result = Supervisor(graph_path, provider, samples=3).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual(result["tasks"]["TASK-001"]["attempts"], 3)
            self.assertEqual(len(provider.prompts), 3)
            self.assertNotIn("Previous deterministic failure", provider.prompts[0])
            self.assertIn("Previous deterministic failure", provider.prompts[1])

    def test_repair_prompt_quotes_the_rejected_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            # A syntax error is a repairable failure: the rejected candidate is
            # quoted so the model can fix it instead of re-deriving from scratch.
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value +\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            provider = _SequenceProvider([bad, good])

            result = Supervisor(graph_path, provider).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertNotIn("Previous candidate", provider.prompts[0])
            self.assertIn(
                "Previous candidate, which failed the gates below; repair it instead of starting over:",
                provider.prompts[1],
            )
            self.assertIn("return value +", provider.prompts[1])
            # The restored original is still shown, so the model can fall back to it.
            self.assertIn("--- current file: src/answer.py ---", provider.prompts[1])
            self.assertIn("return 0", provider.prompts[1])

    def test_candidate_context_skips_a_candidate_identical_to_the_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return 0\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            provider = _SequenceProvider([bad, good])

            result = Supervisor(graph_path, provider).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertNotIn("Previous candidate", provider.prompts[1])

    def test_samples_below_one_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            graph_path = self._project(Path(directory))
            with self.assertRaises(ValueError):
                Supervisor(graph_path, MockProvider([]), samples=0)

    def test_identical_rejected_reply_stops_the_draw_budget_early(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return 0\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            provider = _SequenceProvider([bad, bad, good])

            result = Supervisor(graph_path, provider, samples=3).run()

            task = result["tasks"]["TASK-001"]
            self.assertEqual(task["status"], "FAILED")
            self.assertEqual(task["outcome"], "stagnation")
            self.assertEqual(len(provider.prompts), 2)
            self.assertIn("stagnation", task["failure"])
            self.assertTrue(task["attempt_log"][1]["stagnation"])

    def test_noop_candidate_accepted_by_tests_is_rejected_as_nondiscriminating(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            # A test suite that passes on the unchanged project cannot witness the task.
            always_green = ["python", "-c", "print('always green')"]
            payload["tasks"][0]["test_command"] = always_green
            payload["tasks"][0]["regression_command"] = always_green
            graph_path.write_text(json.dumps(payload))
            original = (root / "src" / "answer.py").read_text()
            unchanged = json.dumps({"files": {"src/answer.py": original}})
            provider = _SequenceProvider([unchanged])

            result = Supervisor(graph_path, provider).run()

            task = result["tasks"]["TASK-001"]
            self.assertEqual(task["status"], "FAILED")
            self.assertIn("do not discriminate", task["failure"])
            self.assertEqual((root / "src" / "answer.py").read_text(), original)

    def test_assertion_failure_prompts_a_fresh_derivation_without_the_rejected_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 1
            graph_path.write_text(json.dumps(payload))
            bad = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return 0\n"}})
            good = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})
            provider = _SequenceProvider([bad, good])

            result = Supervisor(graph_path, provider).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            # A failing-test verdict is a logic failure: the failure text carries
            # forward, but the rejected candidate is not quoted for repair.
            self.assertIn("Previous deterministic failure", provider.prompts[1])
            self.assertNotIn("Previous candidate", provider.prompts[1])

    def test_failure_routing_classifies_repairable_versus_logic_failures(self):
        from cdavc.supervisor import _is_repairable

        self.assertTrue(_is_repairable("provider response must be JSON with a files object"))
        self.assertTrue(_is_repairable("answer.py: SyntaxError: invalid syntax"))
        self.assertTrue(_is_repairable("targeted test failed:\nTraceback (most recent call last):\nTypeError: int() takes 1 argument"))
        # An assertion inside a traceback is still a logic failure.
        self.assertFalse(_is_repairable("targeted test failed:\nTraceback (most recent call last):\nAssertionError: 0 != 2"))
        self.assertFalse(_is_repairable("regression test failed:\nFAILED (failures=1)"))
        self.assertFalse(_is_repairable(""))

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

    def test_supervisor_accepts_unescaped_quotes_in_candidate_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            response = '''{"files": {"src/answer.py": "def answer(value: int) -> int:
    label = "answer"
    return value + len(label) - 5
"}}'''

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertIn('label = "answer"', (root / "src" / "answer.py").read_text())

    def test_unavailable_provider_stops_the_run_without_using_a_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            provider = _UnavailableProvider()

            with self.assertRaises(ProviderUnavailableError):
                Supervisor(graph_path, provider).run()

            self.assertEqual(provider.calls, 1)

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

    def test_prompt_shows_the_tests_and_the_current_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            provider = _CapturingProvider(json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}}))

            Supervisor(graph_path, provider).run()

            prompt = provider.prompts[0]
            self.assertIn("--- test file: tests/test_answer.py ---", prompt)
            self.assertIn("self.assertEqual(answer(41), 42)", prompt)
            self.assertIn("--- current file: src/answer.py ---", prompt)
            self.assertIn("return 0", prompt)
            self.assertIn('"edits"', prompt)

    def test_exact_once_edits_change_only_the_matched_region(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            response = json.dumps({"edits": [{"file": "src/answer.py", "find": "return 0", "replace": "return value + 1"}]})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual((root / "src" / "answer.py").read_text(), "def answer(value: int) -> int:\n    return value + 1\n")

    def test_model_can_retrieve_omitted_tail_context_without_spending_a_draw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph = self._project(root)
            (root / "src/answer.py").write_text(
                "def answer(value):\n    return value + NEEDLE\n" + "# padding line\n" * 1000 + "NEEDLE = 0\n")
            provider = _SequenceProvider([
                json.dumps({"context_search": "NEEDLE"}),
                json.dumps({"edits": [{"file": "src/answer.py", "find": "NEEDLE = 0", "replace": "NEEDLE = 1"}]}),
            ])
            result = Supervisor(graph, provider, context_budget_chars=2000).run()["tasks"]["TASK-001"]
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["attempts"], 1)
            self.assertNotIn("NEEDLE = 0", provider.prompts[0])
            self.assertIn("NEEDLE = 0", provider.prompts[1])
            self.assertEqual(result["accounting"]["calls"], 2)
            self.assertEqual(result["call_log"][1]["purpose"], "context_retrieval")

    def test_invalid_second_edit_cannot_partially_change_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph = self._project(root)
            supervisor = Supervisor(graph, MockProvider([]))
            original = (root / "src/answer.py").read_bytes()
            payload = {"edits": [
                {"file": "src/answer.py", "find": "return 0", "replace": "return value + 1"},
                {"file": "src/answer.py", "find": "not present", "replace": "ignored"},
            ]}
            with self.assertRaises(ValueError):
                supervisor._apply_response(supervisor.graph.tasks[0], json.dumps(payload))
            self.assertEqual((root / "src/answer.py").read_bytes(), original)

    def test_published_candidate_preserves_the_exact_verified_crlf_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph = self._project(root)
            (root / "tests/test_answer.py").write_text(
                "import unittest\nfrom src.answer import answer\n"
                "class T(unittest.TestCase):\n    def test_answer(self): self.assertTrue(answer(41))\n")
            body = ("from pathlib import Path\r\n"
                    "def answer(value):\r\n    return bytes([13, 10]) in Path(__file__).read_bytes()\r\n")
            result = Supervisor(graph, MockProvider([json.dumps({"files": {"src/answer.py": body}})])).run()
            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual((root / "src/answer.py").read_bytes(), body.encode())

    def test_ambiguous_edit_is_rejected_and_the_file_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            (root / "src" / "answer.py").write_text(
                "def answer(value: int) -> int:\n    if value < 0:\n        return 0\n    return 0\n"
            )
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            graph_path.write_text(json.dumps(payload))
            original = (root / "src" / "answer.py").read_text()
            response = json.dumps({"edits": [{"file": "src/answer.py", "find": "return 0", "replace": "return value + 1"}]})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("must match exactly once", result["tasks"]["TASK-001"]["failure"])
            self.assertEqual((root / "src" / "answer.py").read_text(), original)

    def test_dry_run_leaves_the_project_untouched_and_reports_the_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            original = (root / "src" / "answer.py").read_text()
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response]), dry_run=True).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual((root / "src" / "answer.py").read_text(), original)
            diff = result["tasks"]["TASK-001"]["diff"]
            self.assertIn("--- a/src/answer.py", diff)
            self.assertIn("+    return value + 1", diff)
            self.assertTrue((root / "execution_patch.diff").exists())

    def test_regression_gate_rejects_a_suite_that_runs_no_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            (root / "empty_tests").mkdir()
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            payload["regression_command"] = ["python", "-m", "unittest", "discover", "-s", "empty_tests"]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("ran no tests", result["tasks"]["TASK-001"]["failure"])
            self.assertIn("--regression", result["tasks"]["TASK-001"]["failure"])

    def test_targeted_gate_rejects_a_suite_that_runs_no_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            (root / "empty_tests").mkdir()
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            payload["tasks"][0]["test_command"] = ["python", "-m", "unittest", "discover", "-s", "empty_tests"]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "FAILED")
            self.assertIn("--test-command", result["tasks"]["TASK-001"]["failure"])

    def test_test_command_keeps_a_pasted_environment_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["max_retries"] = 0
            payload["tasks"][0]["test_command"] = [
                "CDAVC_MARKER=on",
                "PYTHONPATH=src",
                "python",
                "-c",
                "import os, sys; sys.exit(0 if os.environ.get('CDAVC_MARKER') == 'on' else 'CDAVC_MARKER was not passed to the command')",
            ]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"src/answer.py": "def answer(value: int) -> int:\n    return value + 1\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")

    def test_non_python_implementation_file_skips_the_ast_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_path = self._project(root)
            (root / "web").mkdir()
            (root / "web" / "app.js").write_text("export const answer = 0;\n")
            payload = json.loads(graph_path.read_text())
            payload["tasks"][0]["implementation_files"] = ["web/app.js"]
            payload["tasks"][0]["symbols"] = []
            payload["tasks"][0]["test_command"] = None
            payload["tasks"][0]["regression_command"] = ["python", "-c", "pass"]
            graph_path.write_text(json.dumps(payload))
            response = json.dumps({"files": {"web/app.js": "export const answer = 42;\n"}})

            result = Supervisor(graph_path, MockProvider([response])).run()

            self.assertEqual(result["tasks"]["TASK-001"]["status"], "COMPLETED")
            self.assertEqual((root / "web" / "app.js").read_text(), "export const answer = 42;\n")


if __name__ == "__main__":
    unittest.main()
