"""Validate a complete candidate before applying any filesystem changes."""

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _safe_target(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\x00' in relative:
        raise ValueError('file paths must be nonempty strings')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != relative:
        raise ValueError(f'noncanonical repository-relative path: {relative}')
    # Resolve the root once: on macOS temporary workspaces live under /var,
    # a symlink to /private/var, and an unresolved root never contains the
    # resolved target even when the path is entirely inside the workspace.
    root = Path(root).resolve()
    target = root / path
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f'symlink target is forbidden: {relative}')
    if root not in target.resolve().parents:
        raise ValueError(f'path escapes repository: {relative}')
    if target.exists() and not target.is_file():
        raise ValueError(f'target is not a regular file: {relative}')
    return target


def apply_candidate(root: Path, implementation_files: Sequence[str], payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Apply replacements and original-coordinate exact edits as one transaction.

    Digests are SHA-256 of original raw bytes. Disjoint edits always match the
    original text, never text introduced by another edit. Returns sorted targets.
    """
    root = Path(root).resolve()
    if not root.is_dir() or not isinstance(payload, Mapping):
        raise ValueError('expected a repository directory and candidate object')
    if isinstance(implementation_files, (str, bytes)):
        raise ValueError('implementation_files must be a sequence of paths')
    targets = {name: _safe_target(root, name) for name in implementation_files}
    files, edits = payload.get('files', {}), payload.get('edits', [])
    if not isinstance(files, Mapping) or not isinstance(edits, list) or not (files or edits):
        raise ValueError('candidate needs a files object or an edits list')
    original: dict[str, bytes | None] = {}
    staged: dict[str, bytes] = {}
    ranges: dict[str, list[tuple[int, int, str]]] = {}

    def capture(name: Any) -> bytes | None:
        if not isinstance(name, str) or name not in targets:
            raise ValueError('unknown implementation target')
        if name not in original:
            path = targets[name]
            original[name] = path.read_bytes() if path.exists() else None
        return original[name]

    for name, content in files.items():
        capture(name)
        if not isinstance(content, str):
            raise ValueError('file contents must be strings')
        try:
            staged[name] = content.encode('utf-8')
        except UnicodeError as exc:
            raise ValueError('file contents must be valid UTF-8') from exc
    for edit in edits:
        if not isinstance(edit, Mapping):
            raise ValueError('each edit must be an object')
        name, find, replace = edit.get('file'), edit.get('find'), edit.get('replace')
        raw = capture(name)
        if name in files:
            raise ValueError('files and edits cannot target the same file')
        if raw is None or not isinstance(find, str) or not find or not isinstance(replace, str):
            raise ValueError('edit needs an existing file, nonempty find and string replace')
        if 'base_sha256' in edit and edit['base_sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f'base_sha256 mismatch: {name}')
        try:
            text = raw.decode('utf-8')
            replace.encode('utf-8')
        except UnicodeError as exc:
            raise ValueError('edits require valid UTF-8') from exc
        start = text.find(find)
        if start < 0 or text.find(find, start + 1) >= 0:
            raise ValueError(f'find must match exactly once: {name}')
        end = start + len(find)
        spans = ranges.setdefault(name, [])
        if any(start < old_end and old_start < end for old_start, old_end, _ in spans):
            raise ValueError(f'overlapping edits: {name}')
        spans.append((start, end, replace))
    for name, spans in ranges.items():
        text = original[name].decode('utf-8')
        for start, end, replace in sorted(spans, reverse=True):
            text = text[:start] + replace + text[end:]
        staged[name] = text.encode('utf-8')

    attempted: list[str] = []
    created_dirs: list[Path] = []
    try:
        for name in sorted(staged):
            path = _safe_target(root, name)
            missing = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_dirs.append(directory)
            attempted.append(name)
            path.write_bytes(staged[name])
    except BaseException as failure:
        rollback_errors = []
        for name in reversed(attempted):
            try:
                if original[name] is None:
                    targets[name].unlink(missing_ok=True)
                else:
                    with targets[name].open('wb') as stream:
                        stream.write(original[name])
            except OSError as exc:
                rollback_errors.append(str(exc))
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError as exc:
                rollback_errors.append(str(exc))
        if rollback_errors:
            failure.add_note('rollback failed: ' + '; '.join(rollback_errors))
        raise
    return tuple(sorted(staged))
