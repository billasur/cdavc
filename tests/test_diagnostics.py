import copy
import json
from pathlib import Path
import unittest

from cdavc.diagnostics import render_fixture_report, run_fixture_audit


FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks/verifier_fixtures.json"


class FixtureAuditTests(unittest.TestCase):
    def load(self):
        return json.loads(FIXTURES.read_text())

    def test_frozen_audit_measures_improvement_and_is_reproducible(self):
        fixtures = self.load()
        before = copy.deepcopy(fixtures)
        report = run_fixture_audit(fixtures)
        self.assertEqual(fixtures, before)
        self.assertEqual(report, run_fixture_audit(fixtures))
        self.assertEqual(report["fixture_count"], 10)
        self.assertEqual(report["arms"]["coarse"]["wrong_acceptances"], 6)
        self.assertEqual(report["arms"]["properties"]["wrong_acceptances"], 0)
        for arm in report["arms"].values():
            self.assertEqual(arm["correct_rejections"], 0)
            self.assertEqual(arm["environment_failures"], 0)
            self.assertEqual(arm["coverage"], 1)
        self.assertTrue(report["acceptance_criterion_met"])
        self.assertEqual(len(report["fixture_digest"]), 64)
        for case in report["cases"]:
            for arm in ("coarse", "properties"):
                self.assertEqual(len(case[arm]["artifact_digest"]), 64)
                self.assertEqual(len(case[arm]["evidence_digest"]), 64)
        text = render_fixture_report(report)
        self.assertIn("adversarial", text)
        self.assertIn(report["fixture_digest"], text)
        self.assertNotIn("/tmp/", json.dumps(report))

    def test_configuration_hash_binds_labels_and_source(self):
        fixtures = self.load()
        report = run_fixture_audit(fixtures[:1] + fixtures[4:5])
        fixtures[0]["label"] += " revised"
        changed = run_fixture_audit(fixtures[:1] + fixtures[4:5])
        self.assertNotEqual(report["fixture_digest"], changed["fixture_digest"])

    def test_environment_failure_is_visible_and_cannot_meet_criterion(self):
        fixtures = self.load()
        fixtures = [fixtures[0], fixtures[4]]
        fixtures[0]["files"]["candidate.py"] = "import missing_diagnostic_dependency\ndef solve(x): raise ValueError()\n"
        fixtures[0]["public_check"] = "pass\n"
        report = run_fixture_audit(fixtures)
        self.assertEqual(report["arms"]["properties"]["environment_failures"], 1)
        self.assertEqual(report["arms"]["properties"]["coverage"], 0.5)
        self.assertFalse(report["acceptance_criterion_met"])

    def test_inconclusive_public_check_is_counted_separately(self):
        fixtures = self.load()
        fixtures = [fixtures[0], fixtures[4]]
        fixtures[0]["public_check"] = "print('Ran 0 tests in 0.001s')\n"
        report = run_fixture_audit(fixtures)
        for arm in report["arms"].values():
            self.assertEqual(arm["inconclusive"], 1)
            self.assertEqual(arm["correct_rejections"], 0)
            self.assertEqual(arm["coverage"], 0.5)
        self.assertFalse(report["acceptance_criterion_met"])

    def test_correct_rejection_threshold_is_measured(self):
        fixtures = self.load()
        fixtures[0]["properties"][1]["expected"] = 999
        report = run_fixture_audit(fixtures)
        self.assertEqual(report["delta"]["correct_rejection_rate"], 0.25)
        self.assertFalse(report["acceptance_criterion_met"])
        report = run_fixture_audit(fixtures, max_correct_rejection_increase=0.25)
        self.assertTrue(report["acceptance_criterion_met"])

    def test_validation_precedes_execution(self):
        fixtures = self.load()
        for value in (None, [], fixtures[:1], [fixtures[0], fixtures[0]]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_fixture_audit(value)
        for updates in ({"ground_truth_correct": 1}, {"id": ""}, {"files": {"../bad.py": "pass"}},
                        {"properties": []}, {"timeout_seconds": 100}, {"unknown": 1}):
            changed = copy.deepcopy(fixtures)
            changed[0].update(updates)
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                run_fixture_audit(changed)
        for threshold in (-1, 1.1, True, float("nan"), "0"):
            with self.assertRaises(ValueError):
                run_fixture_audit(fixtures, max_correct_rejection_increase=threshold)
