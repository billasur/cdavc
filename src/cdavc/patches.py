"""Read-only normalization of a strict, textual subset of unified diffs.

Hunks use exact original coordinates: no offset guessing or context searching.
Git's ordinary unquoted a/ and b/ headers and plain unified headers are accepted.
Unsupported metadata or syntax is rejected, never silently discarded.
"""

import re
from collections.abc import Sequence
from pathlib import Path

from .edits import _safe_target


_HUNK = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?\n')
_INDEX = re.compile(r'index [0-9a-f]+\.\.[0-9a-f]+(?: (?:100644|100755))?\n')
_MARKER = '\\ No newline at end of file\n'


def _lines(text: str) -> list[str]:
    """Split only at LF, preserving CR and every original terminator."""
    parts = text.split('\n')
    return [part + '\n' for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _header_path(line: str, prefix: str, side: str) -> str:
    if not line.startswith(prefix) or not line.endswith('\n'):
        raise ValueError('expected complete --- and +++ file headers')
    name = line[len(prefix):-1].split('\t', 1)[0]
    if not name or name.startswith('"') or '\\' in name:
        raise ValueError('quoted or escaped patch paths are unsupported')
    if name.startswith(side + '/'):
        name = name[2:]
    return name


def _test_path(path: str) -> bool:
    parts = Path(path).parts
    return (any(part in {'test', 'tests'} for part in parts[:-1])
            or Path(path).name.startswith('test_')
            or Path(path).name.endswith('_test.py'))


def unified_diff_payload(root: Path, implementation_files: Sequence[str], text: str) -> dict:
    """Return complete UTF-8 file replacements after preflighting every hunk.

    This function never creates, changes, or deletes project files. New files
    require /dev/null as the old path. File deletion, renames, binary changes,
    mode changes, quoted paths, and non-patch prose are unsupported.
    """
    root = Path(root).resolve()
    if not root.is_dir() or not isinstance(text, str) or not text:
        raise ValueError('expected a repository directory and nonempty diff text')
    if not isinstance(implementation_files, Sequence) or isinstance(implementation_files, (str, bytes)):
        raise ValueError('implementation_files must be a sequence of relative paths')
    targets = {}
    for name in implementation_files:
        target = _safe_target(root, name)
        targets[name] = target
    try:
        text.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('diff must be valid UTF-8') from exc
    lines = _lines(text)
    files: dict[str, str] = {}
    i = 0
    while i < len(lines):
        git_path = None
        new_mode = False
        if lines[i].startswith('diff --git '):
            match = re.fullmatch(r'diff --git a/(.+) b/(.+)\n', lines[i])
            if not match or match[1] != match[2] or '"' in match[1] or '\\' in match[1]:
                raise ValueError('unsupported git file header or rename')
            git_path = match[1]
            i += 1
            if i < len(lines) and lines[i] == 'new file mode 100644\n':
                new_mode = True
                i += 1
            if i < len(lines) and _INDEX.fullmatch(lines[i]):
                i += 1
        if i + 1 >= len(lines):
            raise ValueError('file section has no complete headers and hunks')
        old_path = _header_path(lines[i], '--- ', 'a')
        new_path = _header_path(lines[i + 1], '+++ ', 'b')
        i += 2
        if new_path == '/dev/null':
            raise ValueError('file deletion is unsupported')
        is_new = old_path == '/dev/null'
        if (not is_new and old_path != new_path) or (git_path is not None and git_path != new_path):
            raise ValueError('renames or inconsistent file headers are unsupported')
        if new_mode and not is_new:
            raise ValueError('new file metadata requires /dev/null')
        if new_path not in targets or _test_path(new_path):
            raise ValueError(f'patch target is outside implementation contract: {new_path}')
        if new_path in files:
            raise ValueError(f'duplicate patch file section: {new_path}')
        target = _safe_target(root, new_path)
        if is_new:
            if target.exists():
                raise ValueError(f'new file already exists: {new_path}')
            original = []
        else:
            if not target.is_file():
                raise ValueError(f'old file does not exist: {new_path}')
            try:
                original = _lines(target.read_bytes().decode('utf-8'))
            except (OSError, UnicodeError) as exc:
                raise ValueError(f'cannot read UTF-8 patch target: {new_path}') from exc
        output: list[str] = []
        cursor = 0
        previous_start = -1
        hunks = 0
        changed = False
        while i < len(lines) and lines[i].startswith('@@'):
            match = _HUNK.fullmatch(lines[i])
            if match is None:
                raise ValueError('unsupported or malformed hunk header')
            old_line, old_count, new_line, new_count = (
                int(match[1]), int(match[2] or 1), int(match[3]), int(match[4] or 1))
            if (old_count and old_line == 0) or (new_count and new_line == 0) or not (old_count or new_count):
                raise ValueError('invalid hunk coordinates')
            start = old_line - 1 if old_count else old_line
            new_start = new_line - 1 if new_count else new_line
            if start < cursor or (start == previous_start and old_count == 0) or start > len(original):
                raise ValueError('overlapping, duplicate, or out-of-range hunks')
            output.extend(original[cursor:start])
            if new_start != len(output):
                raise ValueError('inconsistent new-line coordinates')
            i += 1
            consumed_old = consumed_new = 0
            body: list[tuple[str, str]] = []
            while True:
                if i < len(lines) and lines[i] == _MARKER:
                    if not body or not body[-1][1].endswith('\n'):
                        raise ValueError('misplaced no-newline marker')
                    kind, value = body[-1]
                    body[-1] = (kind, value[:-1])
                    i += 1
                    continue
                if consumed_old == old_count and consumed_new == new_count:
                    break
                if i >= len(lines) or not lines[i].endswith('\n') or lines[i][:1] not in {' ', '-', '+'}:
                    raise ValueError('truncated or malformed hunk body')
                kind, value = lines[i][0], lines[i][1:]
                consumed_old += kind != '+'
                consumed_new += kind != '-'
                if consumed_old > old_count or consumed_new > new_count:
                    raise ValueError('hunk line counts do not match its header')
                body.append((kind, value))
                changed |= kind != ' '
                i += 1
            expected = [value for kind, value in body if kind != '+']
            replacement = [value for kind, value in body if kind != '-']
            if original[start:start + old_count] != expected:
                raise ValueError(f'stale hunk context at {new_path}:{old_line}')
            output.extend(replacement)
            cursor = start + old_count
            previous_start = start
            hunks += 1
        if not hunks or not changed:
            raise ValueError('file section must contain textual changes')
        output.extend(original[cursor:])
        if any(not line.endswith('\n') for line in output[:-1]):
            raise ValueError('no-newline marker is only valid at end of file')
        files[new_path] = ''.join(output)
        # The outer loop accepts only another complete file section. Any
        # unconsumed metadata, trailer, extra body line, or prose is an error.
    return {'files': files}
