import tempfile
import unittest
from pathlib import Path

from cdavc.launch import build_launch_command


class LaunchTests(unittest.TestCase):
    def test_llama_launch_uses_hardware_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            command = build_launch_command("llama", model, port=8080, memory_bytes=16 * 1024**3)

            self.assertIn("--cache-type-k", command)
            self.assertIn("q8_0", command)
            self.assertIn("--cont-batching", command)

    def test_unknown_backend_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            with self.assertRaises(ValueError):
                build_launch_command("unknown", model, port=8080, memory_bytes=16 * 1024**3)


if __name__ == "__main__":
    unittest.main()
