"""Stable placeholders for machine-specific paths in gate output.

Gate output is fed back to the model and printed to humans, so absolute paths
are replaced with ``$WORKSPACE`` and ``$PROJECT_ROOT``. A subprocess may report
either spelling of a path: on macOS ``/tmp`` is a symlink to ``/private/tmp``,
so a command that resolves a path prints ``/private/tmp/...`` while the harness
holds ``/tmp/...``. Replacing only the second spelling leaves a half-substituted
``/private$WORKSPACE/...`` that names no usable file. Both spellings are
replaced here, longest first, so one cannot clobber a prefix of the other.

A path is only replaced where it ends: ``/tmp/work-backup`` must not become
``$WORKSPACE-backup``. The trailing character check allows a separator, a
punctuation mark or the end of the text.
"""

from __future__ import annotations

import re
from pathlib import Path


def redact_paths(text: str, workspace: Path, root: Path) -> str:
    """Replace absolute workspace and project-root paths with placeholders."""

    replacements: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path, placeholder in ((workspace, "$WORKSPACE"), (root, "$PROJECT_ROOT")):
        for spelling in (str(path), _resolved(path)):
            # A one-character root ("/") would rewrite the entire message.
            if len(spelling) > 1 and spelling not in seen:
                seen.add(spelling)
                replacements.append((spelling, placeholder))
    # Longest first so a workspace nested inside the project root keeps its own
    # placeholder; the sort is stable, so the workspace wins a tie with the root.
    for spelling, placeholder in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        boundary = re.escape(spelling) + r"(?![A-Za-z0-9_\-])"
        text = re.sub(boundary, lambda _match: placeholder, text)
    return text


def _resolved(path: Path) -> str:
    """Return the symlink-resolved spelling, or the given one if it cannot resolve."""

    try:
        return str(Path(path).resolve())
    except (OSError, RuntimeError):
        # A symlink loop makes resolve() raise RuntimeError; the spelling the
        # harness holds is still the one the message may contain.
        return str(path)
