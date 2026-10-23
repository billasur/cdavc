import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cdavc.accounting import Budget
from cdavc.adapters import compare_records, evaluate_external, render_comparison
from cdavc.verification import VerificationContract, WorkspaceSnapshot


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "answer.py").write_text("def answer(): return 0\n")
        (self.root / "check.py").write_text("from answer import answer\nassert answer() == 42\n")
        self.snapshot = WorkspaceSnapshot.capture(self.root)
        self.contract = VerificationContract(implementation_files=("answer.py",), test_files=("check.py",),
                                             symbols=("answer",), test_command=("python", "check.py"))
        self.text = json.dumps({"files": {"answer.py": "def answer(): return 42\n"}})
        self.telemetry = {"complete": True, "calls": [{"prompt_tokens": 10, "completion_tokens": 5}],
                          "wall_time_seconds": 1.0}

    def evaluate(self, source, **kwargs):
        return evaluate_external(self.snapshot, self.contract, self.text, source=source, **kwargs)

    def test_claude_codex_and_local_use_identical_verification_without_claiming_upstream_cost(self):
        rows = [self.evaluate(source) for source in ("claude", "codex", "local")]
        self.assertEqual(rows[0]["verification_evidence"], rows[1]["verification_evidence"])
        self.assertEqual(rows[1]["verification_evidence"], rows[2]["verification_evidence"])
        for row in rows:
            self.assertTrue(row["accepted"])
            self.assertEqual(row["verification_model_calls"], 0)
            self.assertFalse(row["usage_complete"])
            self.assertIsNone(row["provider_calls"])
            self.assertIsNone(row["token_in"])
            self.assertTrue(row["telemetry_limitations"])

    def test_reported_matched_caps_are_qualified_not_a_model_superiority_claim(self):
        budget = Budget(max_calls=2, max_tokens=20, max_wall_seconds=2)
        rows = [self.evaluate(source, telemetry=self.telemetry, budget=budget) for source in ("claude", "codex", "local")]
        report = compare_records(rows)
        self.assertEqual(report["comparison_status"], "matched_reported_budget")
        self.assertTrue(report["token_comparison_complete"])
        text = render_comparison(report)
        self.assertIn("self-reported", text)
        self.assertIn("not a model-superiority", text)

    def test_missing_partial_or_over_budget_telemetry_cannot_claim_matching(self):
        budget = Budget(max_calls=2, max_tokens=20)
        full = self.evaluate("local", telemetry=self.telemetry, budget=budget)
        for telemetry in (None, {"complete": False, "calls": self.telemetry["calls"]},
                          {"complete": True, "calls": [{"prompt_tokens": 30, "completion_tokens": 5}]}):
            with self.subTest(telemetry=telemetry):
                row = self.evaluate("claude", telemetry=telemetry, budget=budget)
                self.assertEqual(compare_records([row, full])["comparison_status"], "inconclusive")

    def test_incompatible_contracts_budgets_and_snapshots_cannot_be_pooled(self):
        baseline = self.evaluate("local", telemetry=self.telemetry, budget=Budget(max_tokens=20))
        other = self.evaluate("claude", telemetry=self.telemetry, budget=Budget(max_tokens=21))
        with self.assertRaisesRegex(ValueError, "incompatible"):
            compare_records([baseline, other])
        changed = evaluate_external(self.snapshot, replace(self.contract, check_repeats=2), self.text,
                                   source="claude", telemetry=self.telemetry, budget=Budget(max_tokens=20))
        with self.assertRaisesRegex(ValueError, "incompatible"):
            compare_records([baseline, changed])

    def test_diff_and_json_produce_the_same_artifact_and_evidence(self):
        patch = "--- a/answer.py\n+++ b/answer.py\n@@ -1 +1 @@\n-def answer(): return 0\n+def answer(): return 42\n"
        diff = evaluate_external(self.snapshot, self.contract, patch, source="codex", format="diff")
        row = self.evaluate("local")
        self.assertEqual(diff["verification_evidence"], row["verification_evidence"])

    def test_unmetered_call_in_export_does_not_turn_into_free_work(self):
        row = self.evaluate("claude", telemetry={"complete": True, "calls": [
            {"prompt_tokens": 10, "completion_tokens": 5}, {"purpose": "repair"}]}, budget=Budget(max_tokens=20))
        self.assertFalse(row["usage_complete"])
        self.assertIsNone(row["token_in"])
        self.assertEqual(row["known_token_in"], 10)
        self.assertEqual(row["reported_provider_calls"], 2)
        self.assertEqual(row["budget_compliance"], "unverifiable")

    def test_invalid_telemetry_and_duplicate_ids_are_rejected(self):
        for telemetry in ({"complete": "yes", "calls": []}, {"calls": [{"prompt_tokens": -1}]},
                          {"calls": [], "wall_time_seconds": float("nan")}):
            with self.subTest(telemetry=telemetry), self.assertRaises(ValueError):
                self.evaluate("local", telemetry=telemetry)
        row = self.evaluate("local")
        with self.assertRaisesRegex(ValueError, "unique"):
            compare_records([row, row])

    def test_edited_record_is_not_silently_pooled(self):
        first = self.evaluate("local", telemetry=self.telemetry, budget=Budget(max_tokens=20))
        second = self.evaluate("claude", telemetry=self.telemetry, budget=Budget(max_tokens=20))
        second["token_in"] = 0
        with self.assertRaisesRegex(ValueError, "corrupt"):
            compare_records([first, second])
