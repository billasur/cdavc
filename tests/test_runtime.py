import tempfile
import unittest
from pathlib import Path

from cdavc.runtime import ModelNotFoundError, build_llama_server_command, find_cached_model


class RuntimeTests(unittest.TestCase):
    def test_finds_preferred_model_in_huggingface_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "hub" / "models--prism-ml--Ternary-Bonsai-2-9B-gguf" / "snapshots" / "abc"
            cache.mkdir(parents=True)
            model = cache / "Ternary-Bonsai-2-9B-PQ2_0-MTP-Q8_0.gguf"
            model.write_bytes(b"model")

            self.assertEqual(find_cached_model(Path(directory) / "hub", "prism-ml/Ternary-Bonsai-2-9B-gguf"), model)

    def test_missing_model_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ModelNotFoundError):
                find_cached_model(Path(directory), "prism-ml/missing")

    def test_mtp_model_command_uses_mtp_flags_and_no_absolute_defaults(self):
        command = build_llama_server_command(Path("/models/bonsai.gguf"), port=8080, context=32768, mtp=True)

        self.assertEqual(command[:3], ["llama-server", "-m", "/models/bonsai.gguf"])
        self.assertIn("--spec-type", command)
        self.assertIn("draft-mtp", command)
        self.assertIn("-c", command)
        self.assertIn("32768", command)


if __name__ == "__main__":
    unittest.main()
