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

    def test_mlx_accepts_a_model_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "mlx-model"
            model.mkdir()
            (model / "weights.safetensors").write_bytes(b"weights")
            command = build_launch_command("mlx", model, port=8080, memory_bytes=16 * 1024**3)

            self.assertIn("--model", command)
            self.assertIn(str(model), command)


if __name__ == "__main__":
    unittest.main()
