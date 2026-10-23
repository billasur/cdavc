import unittest

from cdavc.accounting import Budget, BudgetExceeded, UsageLedger, complete_recorded
from cdavc.providers import MockProvider, ProviderCompletion, ProviderUnavailableError


class AccountingTests(unittest.TestCase):
    def test_unmetered_reask_is_incomplete_not_a_zero_cost_call(self):
        ledger = UsageLedger()
        provider = MockProvider([ProviderCompletion("first", 7, 5), "second"])
        complete_recorded(provider, [], ledger, purpose="generation")
        complete_recorded(provider, [], ledger, purpose="json_reask")
        summary = ledger.summary()
        self.assertEqual(summary["calls"], 2)
        self.assertFalse(summary["usage_complete"])
        self.assertEqual(summary["token_usage_source"], "provider_partial")
        self.assertIsNone(summary["token_in"])
        self.assertIsNone(summary["token_out"])
        self.assertEqual(summary["known_token_in"], 7)
        self.assertEqual(summary["known_token_out"], 5)
        self.assertEqual(ledger.entries[1]["purpose"], "json_reask")

    def test_failed_request_is_recorded_without_inventing_usage(self):
        ledger = UsageLedger()
        with self.assertRaises(ProviderUnavailableError):
            complete_recorded(MockProvider([]), [], ledger)
        self.assertEqual(ledger.summary()["calls"], 1)
        self.assertEqual(ledger.entries[0]["status"], "error")
        self.assertFalse(ledger.summary()["usage_complete"])

    def test_call_budget_includes_json_reasks(self):
        ledger = UsageLedger(Budget(max_calls=1))
        provider = MockProvider([ProviderCompletion("first", 1, 1), "second"])
        complete_recorded(provider, [], ledger)
        with self.assertRaises(BudgetExceeded):
            complete_recorded(provider, [], ledger, purpose="json_reask")
        self.assertEqual(len(ledger.entries), 1)
        self.assertEqual(provider.complete([]), "second")

    def test_token_limit_is_checked_after_each_call_and_unknown_is_inconclusive(self):
        for response, outcome in ((ProviderCompletion("large", 6, 5), "budget_exhausted"),
                                  (ProviderCompletion("unknown"), "inconclusive")):
            with self.subTest(outcome=outcome):
                ledger = UsageLedger(Budget(max_tokens=10))
                with self.assertRaises(BudgetExceeded) as caught:
                    complete_recorded(MockProvider([response]), [], ledger)
                self.assertEqual(caught.exception.outcome, outcome)
                self.assertEqual(len(ledger.entries), 1)

    def test_wall_budget_blocks_calls_without_sleeping(self):
        ticks = iter([0.0, 2.0])
        ledger = UsageLedger(Budget(max_wall_seconds=1), clock=lambda: next(ticks))
        with self.assertRaises(BudgetExceeded):
            complete_recorded(MockProvider(["unused"]), [], ledger)
        self.assertEqual(ledger.entries, [])

    def test_reasoning_and_cache_details_are_not_double_counted(self):
        completion = ProviderCompletion("x", 10, 8, metadata={"usage": {
            "prompt_tokens_details": {"cached_tokens": 4},
            "completion_tokens_details": {"reasoning_tokens": 5},
        }})
        ledger = UsageLedger()
        complete_recorded(MockProvider([completion]), [], ledger)
        self.assertEqual(ledger.summary()["total_tokens"], 18)
        self.assertEqual(ledger.entries[0]["cached_input_tokens"], 4)
        self.assertEqual(ledger.entries[0]["reasoning_tokens"], 5)

    def test_invalid_limits_are_rejected(self):
        for kwargs in ({"max_calls": True}, {"max_tokens": -1}, {"max_wall_seconds": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Budget(**kwargs)
