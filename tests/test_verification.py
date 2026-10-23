import json
import tempfile
import unittest
from pathlib import Path

from cdavc.verification import ArtifactStore, VerificationContract, WorkspaceSnapshot, verify_candidate
from cdavc.benchmark import BenchmarkRunner, BenchmarkTask
from cdavc.graph import Task, TaskGraph
from cdavc.providers import MockProvider
from cdavc.supervisor import Supervisor
from cdavc.accounting import digest
from cdavc.properties import PropertyCase


class VerificationTests(unittest.TestCase):
    def project(self, root):
        (root / "answer.py").write_text("def answer(value):\n    return 0\n")
        (root / "check.py").write_text("from answer import answer\nassert answer(41) == 42\n")
        return VerificationContract(implementation_files=("answer.py",), test_files=("check.py",),
                                    symbols=("answer",), test_command=("python", "check.py"))

    def test_supervisor_and_benchmark_return_identical_public_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            payload = json.dumps({"files": {"answer.py": "def answer(value): return value + 1\n"}})
            task = Task("T1", "increment", (), contract.implementation_files, contract.test_files,
                        contract.symbols, test_command=contract.test_command, max_retries=0)
            result = Supervisor(None, MockProvider([payload]), root=root,
                                graph=TaskGraph("x", (task,)), dry_run=True).run()
            evidence = result["tasks"]["T1"]["verification_evidence"]
            benchmark_task = BenchmarkTask(task_id="T1", title="increment", **{
                key: value for key, value in contract.to_dict().items() if key != "properties"
            }, max_retries=0)
            runner = BenchmarkRunner(root, lambda _arm, _task: MockProvider([payload]),
                                     tasks=[benchmark_task], records_path=root / "records.jsonl", samples=1)
            cage = next(row for row in runner.run() if row["arm"] == "cdavc")
            self.assertEqual(evidence, cage["verification_evidence"])

    def test_inconclusive_public_evidence_is_exposed_identically_by_both_runners(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            (root / "empty_tests").mkdir()
            command = ("python", "-m", "unittest", "discover", "-s", "empty_tests")
            task = Task("T1", "increment", (), ("answer.py",), ("check.py",), ("answer",),
                        test_command=command, max_retries=0)
            payload = json.dumps({"files": {"answer.py": "def answer(value): return value + 1\n"}})
            cli = Supervisor(None, MockProvider([payload]), root=root, graph=TaskGraph("x", (task,)), dry_run=True).run()["tasks"]["T1"]
            benchmark = BenchmarkRunner(root, lambda _arm, _task: MockProvider([payload]),
                tasks=[BenchmarkTask.from_task(task)], records_path=root / "records.jsonl", samples=1)
            cage = next(row for row in benchmark.run() if row["arm"] == "cdavc")
            self.assertEqual(cli["outcome"], "inconclusive")
            self.assertEqual(cli["verification_evidence"], cage["verification_evidence"])

    def test_same_snapshot_artifact_and_contract_have_identical_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            snapshot = WorkspaceSnapshot.capture(root)
            payload = {"files": {"answer.py": "def answer(value):\n    return value + 1\n"}}
            first = verify_candidate(snapshot, payload, contract)
            second = verify_candidate(snapshot, payload, contract)
            self.assertEqual(first, second)
            self.assertEqual(first["outcome"], "accepted_under_declared_checks")
            self.assertTrue(first["accepted"])
            self.assertEqual((root / "answer.py").read_text(), "def answer(value):\n    return 0\n")

    def test_evaluator_mutation_is_rejected_even_when_command_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            payload = {"files": {"answer.py": (
                "from pathlib import Path\nPath('check.py').write_text('pass')\n"
                "def answer(value):\n    return value + 1\n")}}
            evidence = verify_candidate(WorkspaceSnapshot.capture(root), payload, contract)
            self.assertFalse(evidence["accepted"])
            self.assertIn("immutable", evidence["failure"])
            self.assertIn("assert answer", (root / "check.py").read_text())

    def test_candidate_cannot_change_after_it_is_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            payload = {"files": {"answer.py": (
                "from pathlib import Path\nPath(__file__).write_text('def answer(value): return -1')\n"
                "def answer(value):\n    return value + 1\n")}}
            evidence = verify_candidate(WorkspaceSnapshot.capture(root), payload, contract)
            self.assertFalse(evidence["accepted"])
            self.assertIn("immutable", evidence["failure"])

    def test_failed_property_evidence_digest_covers_the_whole_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            contract = VerificationContract(implementation_files=("answer.py",), test_files=("check.py",),
                symbols=("answer",), test_command=("python", "check.py"), properties=(PropertyCase.from_dict({
                    "name": "negative inputs raise", "file": "answer.py", "symbol": "answer",
                    "args": [-1], "raises": "ValueError"}),))
            evidence = verify_candidate(WorkspaceSnapshot.capture(root),
                {"files": {"answer.py": "def answer(value): return value + 1\n"}}, contract)
            self.assertFalse(evidence["accepted"])
            self.assertTrue(evidence["properties"])
            self.assertEqual(evidence["evidence_digest"], digest({
                key: value for key, value in evidence.items() if key != "evidence_digest"}))

    def test_no_executable_checks_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            contract = VerificationContract(implementation_files=("answer.py",), test_files=("check.py",))
            evidence = verify_candidate(WorkspaceSnapshot.capture(root),
                {"files": {"answer.py": "def answer(value): return value + 1\n"}}, contract)
            self.assertFalse(evidence["accepted"])
            self.assertEqual(evidence["outcome"], "inconclusive")

    def test_fresh_candidate_does_not_inherit_side_effect_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            snapshot = WorkspaceSnapshot.capture(root)
            bad = {"files": {"answer.py": "from pathlib import Path\nPath('poison').write_text('x')\ndef answer(value): return 0\n"}}
            good = {"files": {"answer.py": "from pathlib import Path\nassert not Path('poison').exists()\ndef answer(value): return value + 1\n"}}
            self.assertFalse(verify_candidate(snapshot, bad, contract)["accepted"])
            self.assertTrue(verify_candidate(snapshot, good, contract)["accepted"])

    def test_content_addressed_artifact_store_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            payload = {"files": {"answer.py": "value = 1\n"}}
            key = store.put(payload)
            self.assertEqual(store.get(key), payload)
            self.assertEqual(store.put(payload), key)
            (Path(directory) / f"{key}.json").write_text(json.dumps({"forged": True}))
            with self.assertRaisesRegex(ValueError, "digest"):
                store.get(key)
            with self.assertRaisesRegex(ValueError, "digest"):
                store.put(payload)

    def test_flaky_command_is_inconclusive_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as state:
            root = Path(directory)
            self.project(root)
            counter = Path(state) / "counter"
            script = (f"from pathlib import Path; p=Path({str(counter)!r}); "
                      "n=int(p.read_text()) if p.exists() else 0; p.write_text(str(n+1)); assert n == 0")
            contract = VerificationContract(implementation_files=("answer.py",), test_files=("check.py",),
                symbols=("answer",), test_command=("python", "-c", script), check_repeats=2)
            evidence = verify_candidate(WorkspaceSnapshot.capture(root),
                {"files": {"answer.py": "def answer(value): return value + 1\n"}}, contract)
            self.assertFalse(evidence["accepted"])
            self.assertEqual(evidence["outcome"], "inconclusive")
            self.assertIn("flaky", evidence["failure"])

    def test_source_snapshot_is_frozen_and_private_directories_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.project(root)
            (root / ".ogcode").mkdir()
            (root / ".ogcode" / "private.txt").write_text("must not copy")
            snapshot = WorkspaceSnapshot.capture(root)
            (root / "check.py").write_text("raise AssertionError('new evaluator')")
            with snapshot.materialize() as workspace:
                self.assertFalse((workspace / ".ogcode").exists())
                self.assertIn("assert answer", (workspace / "check.py").read_text())
            self.assertTrue(verify_candidate(snapshot,
                {"files": {"answer.py": "def answer(value): return value + 1\n"}}, contract)["accepted"])

    def test_jsonl_data_is_preserved_and_only_declared_output_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.jsonl").write_text('{"input": 1}\n')
            (root / "records.jsonl").write_text('{"output": 2}\n')
            snapshot = WorkspaceSnapshot.capture(root, exclude_paths=("records.jsonl",))
            with snapshot.materialize() as workspace:
                self.assertEqual((workspace / "data.jsonl").read_text(), '{"input": 1}\n')
                self.assertFalse((workspace / "records.jsonl").exists())

    def test_json_contract_is_immutable_and_unknown_or_malformed_fields_fail(self):
        payload = {"implementation_files": ["answer.py"], "test_files": ["check.py"],
                   "test_command": ["python", "check.py"]}
        contract = VerificationContract.from_dict(payload)
        payload["implementation_files"].append("outside.py")
        self.assertEqual(contract.implementation_files, ("answer.py",))
        for change in ({"extra": True}, {"test_files": [None]}, {"properties": None}, {"symbols": "answer"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                VerificationContract.from_dict({**payload, **change})
