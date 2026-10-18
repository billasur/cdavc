import unittest

from cdavc.optimization import HardwareBudget, choose_runtime_profile


class OptimizationTests(unittest.TestCase):
    def test_small_model_gets_quantized_kv_and_larger_context(self):
        profile = choose_runtime_profile(
            HardwareBudget(total_memory_bytes=16 * 1024**3, model_bytes=2_500_000_000)
        )

        self.assertEqual(profile.kv_cache_type, "q8_0")
        self.assertGreaterEqual(profile.context_tokens, 8192)
        self.assertLessEqual(profile.max_sequences, 2)
        self.assertGreater(profile.prefill_tokens, 0)

    def test_large_model_is_conservative_on_sixteen_gigabytes(self):
        profile = choose_runtime_profile(
            HardwareBudget(total_memory_bytes=16 * 1024**3, model_bytes=7_500_000_000)
        )

        self.assertEqual(profile.context_tokens, 4096)
        self.assertEqual(profile.max_sequences, 1)
        self.assertEqual(profile.kv_cache_type, "q8_0")

    def test_invalid_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_runtime_profile(HardwareBudget(total_memory_bytes=4, model_bytes=8))

        with self.assertRaises(ValueError):
            choose_runtime_profile(HardwareBudget(total_memory_bytes=16, model_bytes=1, reserve_bytes=0))


if __name__ == "__main__":
    unittest.main()
