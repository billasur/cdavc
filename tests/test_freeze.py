"""The held-out corpus is frozen.

`benchmarks/HELDOUT.sha256` pins every file that defines the 30 reported
tasks: the task statements, public / hidden / regression tests, the property
table, and the reference solutions. Any accidental edit after the freeze
breaks this test, which is the point: the held-out numbers are only
interpretable if the corpus was never touched while the method was being
developed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks" / "HELDOUT.sha256"


def _parse_manifest(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        entries.append((digest, name))
    return entries


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HeldOutFreezeTest(unittest.TestCase):
    def test_manifest_exists_and_is_complete(self) -> None:
        self.assertTrue(MANIFEST.is_file(), "benchmarks/HELDOUT.sha256 is missing")
        entries = _parse_manifest(MANIFEST)
        names = {name for _, name in entries}
        self.assertEqual(len(entries), len(names), "duplicate paths in the manifest")
        # 30 task statements + 30 reference solutions + 5 shared data files.
        self.assertEqual(len(entries), 65)
        for required in (
            "benchmarks/tasks.json",
            "benchmarks/public_tests.py",
            "benchmarks/hidden_tests.py",
            "benchmarks/regression_tests.py",
            "benchmarks/properties.json",
        ):
            self.assertIn(required, names)

    def test_every_held_out_file_matches_its_digest(self) -> None:
        mismatched: list[str] = []
        missing: list[str] = []
        for digest, name in _parse_manifest(MANIFEST):
            path = ROOT / name
            if not path.is_file():
                missing.append(name)
            elif _digest(path) != digest:
                mismatched.append(name)
        self.assertEqual(missing, [], f"held-out files are missing: {missing}")
        self.assertEqual(
            mismatched,
            [],
            "held-out files changed after the freeze; revert them instead of "
            f"editing: {mismatched}",
        )

    def test_no_unlisted_held_out_files(self) -> None:
        """A new file under the frozen paths would escape the manifest."""
        listed = {name for _, name in _parse_manifest(MANIFEST)}
        found = {
            str(path.relative_to(ROOT))
            for pattern in ("benchmarks/tasks/*/*.py", "benchmarks/mock_solutions/*/*.py")
            for path in ROOT.glob(pattern)
        }
        self.assertEqual(
            found - listed,
            set(),
            "files were added under a frozen path; the manifest must be "
            "regenerated only with an explicit decision entry",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
