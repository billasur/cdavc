import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from unittest.mock import patch

from cdavc.launch import build_launch_command, main


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

    def test_main_prints_command_without_starting_server(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(["--backend", "llama", "--model", str(model), "--memory-bytes", str(16 * 1024**3)])

            self.assertEqual(status, 0)
            self.assertIn("llama-server", stdout.getvalue())

    def test_main_detects_memory_when_not_explicitly_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch("cdavc.launch.detect_memory_bytes", return_value=16 * 1024**3) as detect:
                status = main(["--backend", "llama", "--model", str(model)])

            self.assertEqual(status, 0)
            self.assertIn("--cache-type-k", stdout.getvalue())
            detect.assert_called_once_with()

    def test_detected_low_memory_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            with patch("cdavc.launch.detect_memory_bytes", return_value=1024**3):
                with self.assertRaisesRegex(ValueError, "exceed total memory"):
                    main(["--backend", "llama", "--model", str(model)])

    def test_main_run_uses_explicit_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.gguf"
            model.write_bytes(b"model")
            status = main([
                "--backend", "llama", "--model", str(model),
                "--memory-bytes", str(16 * 1024**3),
                "--executable", "/usr/bin/true", "--run",
            ])

            self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
