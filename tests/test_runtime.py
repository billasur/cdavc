import tempfile
import unittest
from pathlib import Path

from cdavc.optimization import RuntimeProfile
from cdavc.runtime import (
    ModelNotFoundError,
    build_llama_server_command,
    build_mlx_server_command,
    find_cached_model,
)


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

    def test_cache_preference_selects_first_sorted_matching_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshots = Path(directory) / "models--org--repo" / "snapshots"
            first = snapshots / "z-snapshot" / "model-Q4.gguf"
            preferred = snapshots / "a-snapshot" / "model-Q8.gguf"
            other_preferred = snapshots / "b-snapshot" / "model-Q8.gguf"
            for model in (first, preferred, other_preferred):
                model.parent.mkdir(parents=True, exist_ok=True)
                model.write_bytes(b"model")

            self.assertEqual(
                find_cached_model(Path(directory), "org/repo", preferred_tokens=("q8",)),
                preferred,
            )

    def test_cache_returns_sorted_first_candidate_when_no_preference_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshots = Path(directory) / "models--org--repo" / "snapshots"
            candidates = [snapshots / "b" / "second.gguf", snapshots / "a" / "first.gguf"]
            for model in candidates:
                model.parent.mkdir(parents=True, exist_ok=True)
                model.write_bytes(b"model")

            self.assertEqual(find_cached_model(Path(directory), "org/repo"), candidates[1])

    def test_llama_command_rejects_relative_model_and_invalid_port_or_context(self):
        invalid_calls = [
            lambda: build_llama_server_command(Path("models/model.gguf")),
            lambda: build_llama_server_command(Path("/models/model.gguf"), port=0),
            lambda: build_llama_server_command(Path("/models/model.gguf"), port=65536),
            lambda: build_llama_server_command(Path("/models/model.gguf"), context=255),
        ]
        for call in invalid_calls:
            with self.assertRaises(ValueError):
                call()

    def test_llama_command_includes_profile_bounds_and_mtp_flags(self):
        profile = RuntimeProfile(16384, "q4_0", 3, 1024, 2048)
        command = build_llama_server_command(Path("/models/model.gguf"), profile=profile, mtp=True, executable="custom-llama")

        self.assertEqual(command[:3], ["custom-llama", "-m", "/models/model.gguf"])
        self.assertEqual(command[command.index("--cache-type-k") + 1], "q4_0")
        self.assertEqual(command[command.index("--batch") + 1], "2048")
        self.assertEqual(command[command.index("--ubatch") + 1], "512")
        self.assertEqual(command[command.index("--parallel") + 1], "3")
        self.assertIn("--cont-batching", command)
        self.assertEqual(command[command.index("--spec-draft-n-max") + 1], "2")

    def test_mlx_command_uses_default_and_profile_cache_boundaries(self):
        default_command = build_mlx_server_command(Path("/models/model.gguf"))
        self.assertEqual(
            default_command,
            ["mlx_lm.server", "--model", "/models/model.gguf", "--port", "8080", "--max-kv-size", "8192", "--prefill-step-size", "256"],
        )

        profile = RuntimeProfile(4096, "q8_0", 1, 128, 256)
        profile_command = build_mlx_server_command(Path("/models/model.gguf"), port=65535, profile=profile, executable="mlx-server")
        self.assertEqual(profile_command[-6:], ["--port", "65535", "--max-kv-size", "4096", "--prefill-step-size", "128"])

    def test_mlx_command_rejects_relative_model_and_invalid_port(self):
        with self.assertRaises(ValueError):
            build_mlx_server_command(Path("models/model.gguf"))
        with self.assertRaises(ValueError):
            build_mlx_server_command(Path("/models/model.gguf"), port=-1)
        with self.assertRaises(ValueError):
            build_mlx_server_command(Path("/models/model.gguf"), port=65536)


if __name__ == "__main__":
    unittest.main()
