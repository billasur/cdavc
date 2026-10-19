import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cdavc.benchmark import (
    BenchmarkError,
    BenchmarkRunner,
    BenchmarkTask,
    render_report,
    wilson_interval,
)
from cdavc.providers import MockProvider, ProviderCompletion
from cdavc.replay import replay_records, select_records


GOOD = "def answer() -> int:\n    return 42\n"
BAD = "def answer() -> int:\n    return 0\n"


class ReplayTests(unittest.TestCase):
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
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "test@example.invalid"],
            ["git", "config", "user.name", "CD-AVC tests"],
            ["git", "add", "."],
            ["git", "commit", "-qm", "initial"],
        ):
            subprocess.run(command, cwd=root, check=True, capture_output=True)
        return root

    def _task(self, **kwargs) -> BenchmarkTask:
        values = {
            "task_id": "answer",
            "title": "Implement the answer function",
            "description": "",
            "source": "test-fixture-v1",
            "implementation_files": ("src/answer.py",),
            "test_files": ("tests/test_answer.py",),
            "symbols": ("answer",),
            "test_command": ("python", "-m", "unittest", "tests.test_answer"),
            "regression_command": None,
            "max_retries": 0,
        }
        values.update(kwargs)
        return BenchmarkTask(**values)

    def _response(self, body: str) -> ProviderCompletion:
        return ProviderCompletion(text=json.dumps({"files": {"src/answer.py": body}}))

    def test_wilson_interval_brackets_the_point_estimate(self):
        interval = wilson_interval(28, 30)
        self.assertAlmostEqual(interval["rate"], 28 / 30, places=6)
        self.assertLess(interval["low"], interval["rate"])
        self.assertGreater(interval["high"], interval["rate"])
        # Matches the plan's estimate: 28/30 is ~[79%, 98%], and 27/30 ~[74%, 97%].
        self.assertAlmostEqual(interval["low"], 0.787, places=3)
        self.assertAlmostEqual(interval["high"], 0.982, places=3)
        self.assertAlmostEqual(wilson_interval(27, 30)["low"], 0.744, places=3)
        empty = wilson_interval(0, 0)
        self.assertIsNone(empty["low"])

    def test_report_states_the_interval_and_the_sample_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task()
            records = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([self._response(GOOD)]),
                tasks=[task],
                records_path=root / "records.jsonl",
            ).run()
            report = render_report(records)
            self.assertIn("95% CI", report)
            self.assertIn("Mean samples drawn", report)
            self.assertIn("| `cdavc` | 1 | 1 | 100.0% |", report)

    def test_candidate_store_is_content_addressed_and_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task()

            def run(records_name: str):
                return BenchmarkRunner(
                    root,
                    lambda _arm, _task: MockProvider([self._response(GOOD)]),
                    tasks=[task],
                    records_path=root / records_name,
                ).run()

            first = run("records.jsonl")
            second = run("records2.jsonl")
            cage = next(record for record in first if record["arm"] == "cdavc")
            cage_again = next(record for record in second if record["arm"] == "cdavc")
            self.assertEqual(cage["candidate_sha"], cage_again["candidate_sha"])
            stored = root / cage["candidate_dir"] / "src" / "answer.py"
            self.assertEqual(stored.read_text(), GOOD)

            runner = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([]),
                tasks=[task],
                records_path=root / "records.jsonl",
            )
            replay = runner.verify_candidate(task, root / cage["candidate_dir"])
            self.assertTrue(replay["passed"], replay["failure"])
            self.assertIn("targeted_test", replay["gate_results"])

    def test_replay_records_reproduces_the_stored_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task()
            records_path = root / "records.jsonl"
            BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([self._response(BAD)]),
                tasks=[task],
                records_path=records_path,
            ).run()
            corpus = root / "benchmarks" / "tasks.json"
            corpus.parent.mkdir(exist_ok=True)
            corpus.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "task_id": task.task_id,
                                "title": task.title,
                                "description": task.description,
                                "source": task.source,
                                "implementation_files": list(task.implementation_files),
                                "test_files": list(task.test_files),
                                "symbols": list(task.symbols),
                                "test_command": list(task.test_command),
                                "max_retries": task.max_retries,
                            }
                        ]
                    }
                )
            )
            summary = replay_records(
                records_path,
                root=root,
                tasks_path=corpus,
                out_path=root / "replay.jsonl",
                arm="cdavc",
            )
            self.assertEqual(summary["replayed"], 1)
            self.assertEqual(summary["original_passes"], 0)
            self.assertEqual(summary["replay_passes"], 0)
            self.assertEqual(summary["mismatches"], [])
            outcomes = [json.loads(line) for line in (root / "replay.jsonl").read_text().splitlines()]
            self.assertEqual(outcomes[0]["task_id"], "answer")
            self.assertFalse(outcomes[0]["replay_pass"])

    def test_mutant_kill_rate_is_recorded_for_the_cage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            (root / "benchmarks").mkdir()
            (root / "benchmarks" / "properties.json").write_text(
                json.dumps(
                    {
                        "tasks": {
                            "answer": [
                                {"property": "merge_sorted_multiset", "cases": 4, "pure": True}
                            ]
                        }
                    }
                )
            )
            merge = (
                "def answer() -> int:\n    return 42\n\n"
                "def merge_sorted(left: list, right: list) -> list:\n"
                "    return sorted(list(left) + list(right))\n"
            )
            task = self._task(symbols=("merge_sorted",))
            response = ProviderCompletion(text=json.dumps({"files": {"src/answer.py": merge}}))
            records = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([response]),
                tasks=[task],
                records_path=root / "records.jsonl",
                mutants=2,
            ).run()
            cage = next(record for record in records if record["arm"] == "cdavc")
            self.assertTrue(cage["pass"], cage["failure"])
            self.assertGreaterEqual(cage["mutants_generated"], 1)
            self.assertIsNotNone(cage["mutant_kill_rate"])
            self.assertGreaterEqual(cage["mutant_kill_rate"], 0.0)

    def test_verify_candidate_rejects_a_missing_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._git_project(Path(directory))
            task = self._task()
            runner = BenchmarkRunner(
                root,
                lambda _arm, _task: MockProvider([]),
                tasks=[task],
                records_path=root / "records.jsonl",
            )
            empty = root / "candidates" / "cdavc" / "answer" / "deadbeef"
            empty.mkdir(parents=True)
            with self.assertRaises(BenchmarkError):
                runner.verify_candidate(task, empty)
            with self.assertRaises(BenchmarkError):
                runner.verify_candidate(task, root / "does-not-exist")

    def test_select_records_keeps_the_latest_stored_candidate_per_task(self):
        records = [
            {"task_id": "a", "arm": "cdavc", "candidate_dir": "old"},
            {"task_id": "a", "arm": "cdavc", "candidate_dir": "new"},
            {"task_id": "a", "arm": "baseline_single", "candidate_dir": "b"},
            {"task_id": "b", "arm": "cdavc"},
        ]
        selected = select_records(records, arm="cdavc")
        self.assertEqual([item["candidate_dir"] for item in selected], ["new"])


if __name__ == "__main__":
    unittest.main()
