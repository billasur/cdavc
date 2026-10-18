"""Local model discovery and reproducible llama.cpp command construction."""

from __future__ import annotations

from pathlib import Path

from .optimization import RuntimeProfile


class ModelNotFoundError(FileNotFoundError):
    """Raised when a requested local model is absent from the cache."""


def find_cached_model(cache_root: Path, repository: str, *, preferred_tokens: tuple[str, ...] = ()) -> Path:
    """Find a GGUF file in a Hugging Face Hub cache without downloading anything."""
    cache_dir = cache_root / f"models--{repository.replace('/', '--')}"
    snapshots = cache_dir / "snapshots"
    candidates = sorted(path for path in snapshots.glob("*/**/*.gguf") if path.is_file())
    if not candidates:
        raise ModelNotFoundError(
            f"No GGUF model found for {repository} under {snapshots}. "
            "Download it first or pass a different cache root."
        )
    for token in preferred_tokens:
        matching = [path for path in candidates if token.lower() in path.name.lower()]
        if matching:
            return matching[0]
    return candidates[0]


def build_llama_server_command(
    model_path: Path,
    *,
    port: int = 8080,
    context: int = 32768,
    mtp: bool = False,
    profile: RuntimeProfile | None = None,
    executable: str = "llama-server",
) -> list[str]:
    """Build a local OpenAI-compatible server command without starting it."""
    if not model_path.is_absolute():
        raise ValueError("model_path must be absolute when launching a local runtime")
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    if context < 256:
        raise ValueError("context must be at least 256 tokens")
    command = [executable, "-m", str(model_path), "-ngl", "99", "-fa", "on", "-c", str(context), "--port", str(port)]
    if profile is not None:
        command.extend([
            "--cache-type-k", profile.kv_cache_type,
            "--cache-type-v", profile.kv_cache_type,
            "--batch", str(profile.batch_tokens),
            "--ubatch", str(min(profile.batch_tokens, 512)),
            "--parallel", str(profile.max_sequences),
            "--cont-batching",
        ])
    if mtp:
        command.extend(["--spec-type", "draft-mtp", "--spec-draft-n-max", "2", "--spec-draft-n-min", "0", "--spec-draft-p-min", "0"])
    return command


def build_mlx_server_command(
    model_path: Path,
    *,
    port: int = 8080,
    profile: RuntimeProfile | None = None,
    executable: str = "mlx_lm.server",
) -> list[str]:
    """Build an MLX-LM server command using bounded cache and prefill settings."""
    if not model_path.is_absolute():
        raise ValueError("model_path must be absolute when launching a local runtime")
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    chosen = profile or RuntimeProfile(8192, "q8_0", 1, 256, 256)
    return [
        executable,
        "--model", str(model_path),
        "--port", str(port),
        "--max-kv-size", str(chosen.context_tokens),
        "--prefill-step-size", str(chosen.prefill_tokens),
    ]
