"""Launch or print a hardware-aware local inference server command."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .optimization import HardwareBudget, choose_runtime_profile
from .runtime import build_llama_server_command, build_mlx_server_command


def detect_memory_bytes() -> int:
    if sys.platform == "darwin":
        result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    page_size = os.sysconf("SC_PAGE_SIZE")
    pages = os.sysconf("SC_PHYS_PAGES")
    return page_size * pages


def build_launch_command(
    backend: str,
    model_path: Path,
    *,
    port: int,
    memory_bytes: int | None = None,
    executable: str | None = None,
) -> list[str]:
    if not model_path.is_absolute() or not model_path.is_file():
        raise ValueError("model path must be an existing absolute file or directory")
    model_bytes = model_path.stat().st_size if model_path.is_file() else 0
    profile = choose_runtime_profile(HardwareBudget(memory_bytes or detect_memory_bytes(), model_bytes))
    if backend == "llama":
        return build_llama_server_command(model_path, port=port, context=profile.context_tokens, mtp="MTP" in model_path.name, profile=profile, executable=executable or "llama-server")
    if backend == "mlx":
        return build_mlx_server_command(model_path, port=port, profile=profile)
    raise ValueError("backend must be 'llama' or 'mlx'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch an optimized local model server")
    parser.add_argument("--backend", choices=("llama", "mlx"), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--memory-bytes", type=int)
    parser.add_argument("--executable", help="override llama-server or mlx_lm.server")
    parser.add_argument("--run", action="store_true", help="execute the server; otherwise print the command")
    args = parser.parse_args(argv)
    command = build_launch_command(args.backend, args.model, port=args.port, memory_bytes=args.memory_bytes, executable=args.executable)
    print(" ".join(command))
    if args.run:
        return subprocess.run(command).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
