"""Structural checks for the dev corpus.

The dev corpus is where every iteration is allowed to read failures, so its
integrity matters as much as the held-out freeze: it must stay disjoint from
the reported tasks, keep 40+ tasks, and remain byte-identical to its manifest
while a phase is running.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "benchmarks" / "dev"


class DevCorpusTest(unittest.TestCase):
    def test_dev_corpus_has_at_least_forty_tasks(self) -> None:
        payload = json.loads((DEV / "tasks.json").read_text())
        tasks = payload["tasks"]
        self.assertGreaterEqual(len(tasks), 40)
        self.assertEqual(len({task["task_id"] for task in tasks}), len(tasks))
        for task in tasks:
            self.assertEqual(task["source"], "CD-AVC-dev-v1")
            self.assertTrue((ROOT / task["implementation_files"][0]).is_file())
            self.assertTrue(task["test_command"] and task["hidden_test_command"])
            self.assertEqual(task["test_command"][-1], task["task_id"])

    def test_dev_tasks_are_disjoint_from_held_out(self) -> None:
        dev = json.loads((DEV / "tasks.json").read_text())["tasks"]
        held = json.loads((ROOT / "benchmarks" / "tasks.json").read_text())["tasks"]
        dev_symbols = {symbol for task in dev for symbol in task["symbols"]}
        held_symbols = {symbol for task in held for symbol in task["symbols"]}
        self.assertEqual(dev_symbols & held_symbols, set())
        self.assertEqual({task["task_id"] for task in dev} & {task["task_id"] for task in held}, set())

    def test_every_dev_task_has_a_reference_and_a_property(self) -> None:
        dev = json.loads((DEV / "tasks.json").read_text())["tasks"]
        table = json.loads((DEV / "properties.json").read_text())["tasks"]
        for task in dev:
            task_id = task["task_id"]
            self.assertTrue((DEV / "references" / f"{task_id}.py").is_file())
            entries = table[task_id]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["property"], "dev_reference_matches")
            self.assertEqual(entries[0]["symbol"], task["symbols"][0])
            self.assertTrue((ROOT / entries[0]["reference"]).is_file())

    def test_dev_manifest_matches_the_tree(self) -> None:
        manifest = DEV / "MANIFEST.sha256"
        self.assertTrue(manifest.is_file())
        listed = set()
        for line in manifest.read_text().splitlines():
            if not line.strip():
                continue
            digest, _, name = line.partition("  ")
            path = ROOT / name
            self.assertTrue(path.is_file(), f"manifest lists a missing file: {name}")
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                digest,
                f"dev corpus changed after hashing: {name}",
            )
            listed.add(name)
        found = {
            path.relative_to(ROOT).as_posix()
            for pattern in ("tasks/*/solution.py", "references/*.py", "*.py", "*.json")
            for path in DEV.glob(pattern)
        } - {"benchmarks/dev/MANIFEST.sha256"}
        self.assertEqual(found - listed, set(), "dev files missing from the manifest")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
