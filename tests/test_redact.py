"""Path placeholders must survive a symlink-resolved spelling of the same path."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cdavc.redact import redact_paths


class RedactPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name).resolve()
        self.root = self.base / "project"
        self.workspace = self.base / "workspace"
        self.root.mkdir()
        self.workspace.mkdir()

    def test_plain_spelling_is_replaced(self) -> None:
        text = f"Traceback: {self.workspace}/benchmarks/public_tests.py\nfrom {self.root}/src"

        redacted = redact_paths(text, self.workspace, self.root)

        self.assertEqual(redacted, "Traceback: $WORKSPACE/benchmarks/public_tests.py\nfrom $PROJECT_ROOT/src")

    def test_resolved_spelling_is_replaced(self) -> None:
        """A command that resolves its own paths prints the symlink target."""

        link = self.base / "link"
        link.symlink_to(self.base, target_is_directory=True)
        spelled = link / "workspace"
        self.assertNotEqual(str(spelled), str(spelled.resolve()))

        redacted = redact_paths(f"could not load {spelled.resolve()}/solution.py", spelled, self.root)

        self.assertEqual(redacted, "could not load $WORKSPACE/solution.py")

    def test_workspace_inside_root_keeps_its_own_placeholder(self) -> None:
        nested = self.root / "work"
        nested.mkdir()

        redacted = redact_paths(f"{nested}/a.py and {self.root}/b.py", nested, self.root)

        self.assertEqual(redacted, "$WORKSPACE/a.py and $PROJECT_ROOT/b.py")

    def test_filesystem_root_is_not_redacted(self) -> None:
        text = "/usr/bin/python and /etc/hosts"

        self.assertEqual(redact_paths(text, Path("/"), Path("/")), text)

    def test_identical_workspace_and_root_uses_the_workspace_name(self) -> None:
        """`cdavc run` may pass the project root as both paths; the name must not flip."""

        redacted = redact_paths(f"{self.workspace}/a.py", self.workspace, self.workspace)

        self.assertEqual(redacted, "$WORKSPACE/a.py")

    def test_longer_sibling_path_is_not_redacted(self) -> None:
        text = f"{self.workspace}-backup/a.py and {self.workspace}/b.py"

        redacted = redact_paths(text, self.workspace, self.root)

        self.assertEqual(redacted, f"{self.workspace}-backup/a.py and $WORKSPACE/b.py")

    def test_path_followed_by_punctuation_is_redacted(self) -> None:
        redacted = redact_paths(f"failed at {self.workspace}.", self.workspace, self.root)

        self.assertEqual(redacted, "failed at $WORKSPACE.")

    def test_symlink_loop_does_not_raise(self) -> None:
        first = self.base / "loop-a"
        second = self.base / "loop-b"
        first.symlink_to(second)
        second.symlink_to(first)

        redacted = redact_paths(f"{first}/x.py", first, self.root)

        self.assertEqual(redacted, "$WORKSPACE/x.py")


if __name__ == "__main__":
    unittest.main()
