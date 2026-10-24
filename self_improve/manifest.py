"""Pinned manifest for the fixed evaluation authority.

The manifest holds SHA-256 hashes of every protected file (the protected task
list and every file under benchmarks_dev2 and benchmarks_heldout). The
controller verifies the working tree against this manifest before every
iteration AND after every evaluation, so an edit made mid-run is caught too.

Honest scope: this detects changes by a cooperating-or-careless agent and any
edit made through normal file writes, including edits the pi extension's
write guard misses (bash, git reset, symlinks resolving into protected
paths). It is NOT a security boundary against an adversarial agent with
unrestricted shell and git access in this repo: such an agent could rewrite
this manifest or the controller itself. Real isolation needs enforcement
outside the repo (read-only mount, separate OS user, or CI-side evaluation),
which this sandbox cannot provide. docs/SELF_IMPROVE.md says the same.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# The whole loop (controller, evaluators, proposers, protected task list) is
# outside the candidate-editable scope; only harness_config.json may change.
# IMPROVE_LOG.md is append-only runtime output and runs/ holds run records.
PROTECTED_ROOTS = ("self_improve", "src/cdavc", "benchmarks_dev2", "benchmarks_heldout")
EXCLUDED_NAMES = {"MANIFEST.sha256", "IMPROVE_LOG.md", "harness_config.json"}
EXCLUDED_DIRS = {"runs", "__pycache__"}
MANIFEST_PATH = Path(__file__).parent / "protected" / "MANIFEST.sha256"


class ManifestMismatchError(RuntimeError):
    """A protected file differs from the pinned manifest."""


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(repo_root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for root in PROTECTED_ROOTS:
        base = Path(repo_root) / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name in EXCLUDED_NAMES:
                continue
            if any(part in EXCLUDED_DIRS for part in path.relative_to(base).parts):
                continue
            entries[path.relative_to(repo_root).as_posix()] = _hash(path)
    return entries


def write_manifest(repo_root: Path) -> int:
    entries = build_manifest(repo_root)
    body = json.dumps(entries, indent=1, sort_keys=True) + "\n"
    (Path(repo_root) / MANIFEST_PATH.name)  # noqa: B018 - clarity
    manifest_file = Path(repo_root) / "self_improve" / "protected" / "MANIFEST.sha256"
    manifest_file.write_text(body)
    return len(entries)


def verify_manifest(repo_root: Path) -> None:
    manifest_file = Path(repo_root) / "self_improve" / "protected" / "MANIFEST.sha256"
    expected = json.loads(manifest_file.read_text())
    problems: list[str] = []
    for rel, want in expected.items():
        path = Path(repo_root) / rel
        if path.is_symlink():
            problems.append(f"{rel}: is now a symlink")
        elif not path.is_file():
            problems.append(f"{rel}: missing")
        elif _hash(path) != want:
            problems.append(f"{rel}: content changed")
    current = build_manifest(repo_root)
    for rel in set(current) - set(expected):
        problems.append(f"{rel}: unexpected new file in protected tree")
    if problems:
        raise ManifestMismatchError(
            "protected evaluation files differ from the pinned manifest:\n"
            + "\n".join(problems[:20])
        )
