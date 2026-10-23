"""Deterministic, declared-file-only context chunks and budgeted retrieval."""

import ast
import hashlib
import re
from pathlib import Path
from collections.abc import Sequence

from .edits import _safe_target


class ContextIndex:
    def __init__(self, root: Path, paths: Sequence[str], *, chunk_chars: int = 2000):
        if not isinstance(chunk_chars, int) or isinstance(chunk_chars, bool) or chunk_chars <= 0:
            raise ValueError('chunk_chars must be a positive integer')
        if isinstance(paths, (str, bytes)):
            raise ValueError('paths must be a sequence')
        self.root = Path(root).resolve()
        self._chunks: dict[str, tuple[dict, str, str, int, int]] = {}
        # Defined-symbol names per chunk id; ranking signal only, not manifest data.
        self._symbols: dict[str, frozenset[str]] = {}
        for path in sorted(set(paths)):
            target = _safe_target(self.root, path)
            raw = target.read_bytes()
            try:
                text = raw.decode('utf-8')
            except UnicodeError as exc:
                raise ValueError(f'context file is not UTF-8: {path}') from exc
            file_digest = hashlib.sha256(raw).hexdigest()
            regions = _python_regions(text) if path.endswith('.py') else None
            if regions is None:
                self._add_char_chunks(path, text, file_digest, chunk_chars)
            else:
                self._add_region_chunks(path, text, file_digest, regions, chunk_chars)

    def _register(self, path: str, text: str, file_digest: str, start: int, end: int,
                  start_line: int, symbols: frozenset[str]) -> None:
        content = text[start:end]
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        identity = f'{path}\0{file_digest}\0{start}\0{end}'.encode('utf-8')
        chunk_id = hashlib.sha256(identity).hexdigest()[:24]
        end_line = start_line + content.count('\n') - int(content.endswith('\n'))
        metadata = dict(id=chunk_id, path=path, start_line=start_line,
                        end_line=end_line, sha256=digest, chars=len(content))
        self._chunks[chunk_id] = (metadata, content, file_digest, start, end)
        if symbols:
            self._symbols[chunk_id] = symbols

    def _add_char_chunks(self, path: str, text: str, file_digest: str, chunk_chars: int) -> None:
        offset, line = 0, 1
        while offset < len(text):
            end = min(offset + chunk_chars, len(text))
            # Prefer complete lines; hard-split oversized lines.
            boundary = text.rfind('\n', offset, end)
            if boundary >= offset:
                end = boundary + 1
            self._register(path, text, file_digest, offset, end, line, frozenset())
            line += text[offset:end].count('\n')
            offset = end

    def _add_region_chunks(self, path: str, text: str, file_digest: str,
                           regions: list[tuple[int, int, int, frozenset[str]]], chunk_chars: int) -> None:
        """Add Python chunks aligned to top-level statements, size-capped.

        Regions follow statement boundaries so a definition or assignment is
        never cut mid-body when it fits the budget; oversized regions split at
        line boundaries and only the first piece carries the region's defined
        names, because that is where the definition starts.
        """
        line_starts = [0]
        for match in re.finditer(r'\n', text):
            line_starts.append(match.end())
        for start_line, end_line, region_chars, symbols in regions:
            start = line_starts[start_line - 1] if start_line - 1 < len(line_starts) else len(text)
            end = line_starts[end_line] if end_line < len(line_starts) else len(text)
            offset = start
            line = start_line
            while offset < end:
                piece_end = min(offset + chunk_chars, end)
                boundary = text.rfind('\n', offset, piece_end)
                if boundary >= offset:
                    piece_end = boundary + 1
                self._register(path, text, file_digest, offset, piece_end, line,
                               symbols if offset == start else frozenset())
                line += text[offset:piece_end].count('\n')
                offset = piece_end

    def manifest(self) -> list[dict]:
        return [dict(entry[0]) for entry in self._chunks.values()]

    def retrieve(self, chunk_id: str) -> str:
        if not isinstance(chunk_id, str) or chunk_id not in self._chunks:
            raise ValueError('unknown context chunk id')
        metadata, _, file_digest, start, end = self._chunks[chunk_id]
        target = _safe_target(self.root, metadata['path'])
        try:
            raw = target.read_bytes()
            if hashlib.sha256(raw).hexdigest() != file_digest:
                raise ValueError('stale context chunk; rebuild the index')
            content = raw.decode('utf-8')[start:end]
        except (OSError, UnicodeError) as exc:
            raise ValueError('context file is unavailable or changed') from exc
        if hashlib.sha256(content.encode('utf-8')).hexdigest() != metadata['sha256']:
            raise ValueError('context chunk digest mismatch')
        return content

    def ranked(self, query: str) -> list[dict]:
        """Expose relevant IDs even when their source body will not fit a prompt."""
        if not isinstance(query, str):
            raise ValueError('query must be a string')
        terms = set(re.findall(r'\w+', query.lower()))
        def score(chunk_id):
            metadata, content, *_ = self._chunks[chunk_id]
            words = set(re.findall(r'\w+', content.lower()))
            path_words = set(re.findall(r'\w+', metadata['path'].lower()))
            # A query term naming a symbol DEFINED in the chunk is a stronger
            # signal than the same term merely appearing in its body.
            definitions = len(terms & self._symbols.get(chunk_id, frozenset()))
            return -(len(terms & words) * 3 + len(terms & path_words) + definitions * 5)
        # Equal scores pack in reading order, so a bounded prompt prefers a
        # contiguous prefix of the file over arbitrarily scattered pieces.
        return [dict(self._chunks[key][0])
                for key in sorted(self._chunks, key=lambda key: (score(key), self._chunks[key][3], key))]

    def pack(self, query: str, *, max_chars: int) -> dict:
        """Return bounded prompt text plus included/omitted chunk ID lists.

        Metadata lists are out-of-band; every character of prompt text, including
        headers and retrieval instructions, counts against max_chars. Chunks pack
        in rank order and STOP at the first one that does not fit: a bounded
        prompt is a contiguous, score-ordered prefix, never scattered fragments
        of the file with the middle missing.
        """
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 0:
            raise ValueError('max_chars must be a nonnegative integer')
        ranked = [row['id'] for row in self.ranked(query)]
        instruction = 'Source chunks below are exact; omitted source remains retrievable.\n'
        text = instruction if len(instruction) <= max_chars else ''
        included = []
        for chunk_id in ranked:
            metadata = self._chunks[chunk_id][0]
            content = self.retrieve(chunk_id)
            block = (f"\n--- {chunk_id} {metadata['path']} lines "
                     f"{metadata['start_line']}-{metadata['end_line']} ---\n{content}\n")
            if len(text) + len(block) > max_chars:
                break
            text += block
            included.append(chunk_id)
        selected = set(included)
        omitted = [chunk_id for chunk_id in self._chunks if chunk_id not in selected]
        return dict(text=text, included=included, omitted=omitted, used_chars=len(text))


def _python_regions(text: str) -> list[tuple[int, int, int, frozenset[str]]] | None:
    """Partition parsed Python source into contiguous top-level-statement regions.

    Returns ``[(start_line, end_line, char_span, defined_names)]`` covering the
    whole file, or ``None`` when the source does not parse (mid-edit files fall
    back to plain character chunking). Every top-level statement starts a region
    so definitions and assignments stay whole; region starts include decorators
    so they are never severed from their definition, and gaps between statements
    belong to the preceding region.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return None
    total_lines = text.count('\n') + int(bool(text) and not text.endswith('\n'))
    boundaries: list[tuple[int, frozenset[str]]] = []
    for node in tree.body:
        first = min([node.lineno, *(d.lineno for d in getattr(node, 'decorator_list', ()))])
        names = frozenset({node.name}) if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else frozenset()
        boundaries.append((first, names))
    if not boundaries:
        return [(1, max(total_lines, 1), len(text), frozenset())]
    regions: list[tuple[int, int, int, frozenset[str]]] = []
    if boundaries[0][0] > 1:
        regions.append((1, boundaries[0][0] - 1, 0, frozenset()))
    for index, (start, names) in enumerate(boundaries):
        end = boundaries[index + 1][0] - 1 if index + 1 < len(boundaries) else max(total_lines, 1)
        regions.append((start, end, 0, names))
    return regions


class ContextSession:
    """Bounded model-visible context plus an explicit, counted retrieval protocol.

    The catalogue may itself be abbreviated. Search covers every declared chunk,
    so omission from the initial prompt never makes a source tail inaccessible.
    """

    def __init__(self, root: Path, paths: Sequence[str], *, query: str, max_chars: int = 12000,
                 roles: dict[str, str] | None = None):
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 512:
            raise ValueError('context budget must be at least 512 characters')
        self.max_chars = max_chars
        self.query = query
        self.roles = roles or {}
        self.index = ContextIndex(root, paths, chunk_chars=min(2000, max_chars // 3))

    def initial(self) -> str:
        return self._pack(self.query)

    def _pack(self, query: str) -> str:
        prefix = ('Context retrieval (counts as another provider call, not another candidate draw):\n'
                  'Return only {"context_search":"symbol or words"} to search ALL declared source,\n'
                  'or {"context_requests":["chunk_id"]} for exact chunks. Then return the candidate.\n')
        for path, role in self.roles.items():
            header = f'--- {role} file: {path} ---\n'
            if len(prefix) + len(header) <= self.max_chars // 3:
                prefix += header
        catalogue = ''
        for row in self.index.ranked(query):
            line = f"{row['id']} {row['path']}:{row['start_line']}-{row['end_line']}\n"
            if len(catalogue) + len(line) > self.max_chars // 8:
                if not catalogue:
                    catalogue = row['id'] + '\n'
                break
            catalogue += line
        prefix += 'Partial chunk catalogue (search accesses omitted entries):\n' + catalogue
        packed = self.index.pack(query, max_chars=max(0, self.max_chars - len(prefix)))
        return (prefix + packed['text'])[:self.max_chars]

    def respond(self, payload: dict) -> str:
        if not isinstance(payload, dict) or set(payload) not in ({'context_search'}, {'context_requests'}):
            raise ValueError('context request must contain only context_search or context_requests')
        if 'context_search' in payload:
            query = payload['context_search']
            if not isinstance(query, str) or not query.strip() or len(query) > 1000:
                raise ValueError('context_search must be nonempty text of at most 1000 characters')
            return self._pack(query)
        requests = payload['context_requests']
        if (not isinstance(requests, list) or not requests or not all(isinstance(key, str) for key in requests)
                or len(set(requests)) != len(requests)):
            raise ValueError('context_requests must contain unique chunk IDs')
        # Validate/retrieve every request before returning any partial response.
        chunks = [(key, self.index.retrieve(key)) for key in requests]
        text = ''.join(f'\n--- requested chunk {key} ---\n{content}\n' for key, content in chunks)
        if len(text) > self.max_chars:
            raise ValueError('requested context exceeds budget; request fewer chunks')
        return text


def is_context_request(payload) -> bool:
    return isinstance(payload, dict) and bool({'context_search', 'context_requests'} & payload.keys())
