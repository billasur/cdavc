"""Recover a JSON payload from a model reply.

Local models routinely put source code inside a JSON string and forget to
escape the quotes in it (``raise ValueError("Empty text")``), or escape
backslashes that JSON does not allow (``\\d`` in a regular expression).  A
strict :func:`json.loads` rejects the whole candidate, so the payload is
recovered with a small backtracking scan that takes a quote as a string
terminator only when what follows can continue the document.
"""

import json
import re
from collections.abc import Mapping
from typing import Any, Iterator

__all__ = ["parse_payload", "strip_json_fence"]

_MAX_SCAN_STEPS = 20_000
_INVALID_ESCAPE = re.compile(r'\\([^"\\/bfnrtu])')
_INTERIOR_QUOTE_FIX = re.compile(r':\s*"""([\s\S]*?)"""')
_PAYLOAD_START = re.compile(r'\{\s*"(?:files|edits)"\s*:')
_PAYLOAD_KEYS = ("files", "edits")


def strip_json_fence(response: str) -> str:
    """Return the JSON-looking part of a reply, dropping prose and fences."""

    text = response.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = fence_match.group(1).strip() if fence_match else text
    # Slicing here (first '{' .. last '}') would glue an example onto the real
    # answer when a reply contains both; the scan below picks the answer instead.
    return _INTERIOR_QUOTE_FIX.sub(lambda match: ": " + json.dumps(match.group(1)), candidate)


def parse_payload(response: str) -> Any:
    """Decode a provider reply, tolerating the escaping slips models make.

    Raises :class:`ValueError` when no JSON value can be recovered.
    """

    if not isinstance(response, str):
        raise ValueError("provider response is not text")
    text = strip_json_fence(response)
    for candidate in (text, _repair_escapes(text)):
        try:
            return json.loads(candidate, strict=False)
        except (json.JSONDecodeError, TypeError, RecursionError):
            continue
    if not text:
        raise ValueError("provider response is not a JSON object")
    try:
        recovered = _scan_document(text)
    except RecursionError:
        # Nesting deeper than the parser can walk is not a recoverable payload.
        recovered = None
    if recovered is None:
        raise ValueError("provider response is not a JSON object")
    return recovered


def _repair_escapes(text: str) -> str:
    return _INVALID_ESCAPE.sub(r"\\\\\1", text)


def _scan_document(text: str) -> Any:
    """Return the payload-shaped object a reply most likely meant as its answer.

    A reply may show an example before the answer, so every object starting
    with ``files`` or ``edits`` is tried newest first: the answer is the last
    payload in the text.  Anything else (a bare array, an object whose keys
    are ordered differently) is recovered from the first value that reaches the
    end of the text, else the furthest-reaching one, so trailing prose cannot
    shadow a complete reading.
    """

    for match in reversed(list(_PAYLOAD_START.finditer(text))):
        budget = _Budget(_MAX_SCAN_STEPS)
        for value, _end in _scan_value(text, match.start(), budget):
            if isinstance(value, Mapping) and any(key in value for key in _PAYLOAD_KEYS):
                return value
    fallback = None
    furthest = -1
    budget = _Budget(_MAX_SCAN_STEPS)
    for start, character in enumerate(text):
        if character not in "{[":
            continue
        for value, end in _scan_value(text, start, budget):
            if _skip_space(text, end) >= len(text):
                return value
            if end > furthest:
                fallback, furthest = value, end
    return fallback


def _scan_value(text: str, index: int, budget: "_Budget") -> Iterator[tuple[Any, int]]:
    if index >= len(text) or not budget.spend():
        return
    character = text[index]
    if character == "{":
        yield from _scan_object(text, index, budget)
    elif character == "[":
        yield from _scan_array(text, index, budget)
    elif character == '"':
        yield from _scan_string(text, index)
    else:
        try:
            value, end = _DECODER.raw_decode(text, index)
        except ValueError:
            return
        yield value, end


def _scan_object(text: str, index: int, budget: "_Budget") -> Iterator[tuple[Any, int]]:
    yield from _scan_members(text, index + 1, budget, [])


def _scan_members(
    text: str, index: int, budget: "_Budget", pairs: list[tuple[str, Any]]
) -> Iterator[tuple[Any, int]]:
    if not budget.spend():
        return
    index = _skip_space(text, index)
    if index < len(text) and text[index] == "}":
        yield dict(pairs), index + 1
        return
    if pairs:
        if index >= len(text) or text[index] != ",":
            return
        index = _skip_space(text, index + 1)
    for key, after_key in _scan_string(text, index):
        colon = _skip_space(text, after_key)
        if colon >= len(text) or text[colon] != ":":
            continue
        for value, after_value in _scan_value(text, _skip_space(text, colon + 1), budget):
            pairs.append((key, value))
            yield from _scan_members(text, after_value, budget, pairs)
            pairs.pop()


def _scan_array(text: str, index: int, budget: "_Budget") -> Iterator[tuple[Any, int]]:
    yield from _scan_items(text, index + 1, budget, [])


def _scan_items(
    text: str, index: int, budget: "_Budget", values: list[Any]
) -> Iterator[tuple[Any, int]]:
    if not budget.spend():
        return
    index = _skip_space(text, index)
    if index < len(text) and text[index] == "]":
        yield list(values), index + 1
        return
    if values:
        if index >= len(text) or text[index] != ",":
            return
        index = _skip_space(text, index + 1)
    for value, after_value in _scan_value(text, index, budget):
        values.append(value)
        yield from _scan_items(text, after_value, budget, values)
        values.pop()


def _scan_string(text: str, index: int) -> Iterator[tuple[str, int]]:
    """Yield every quote that could close the string starting at ``index``."""

    if index >= len(text) or text[index] != '"':
        return
    position = index + 1
    while position < len(text):
        character = text[position]
        if character == "\\":
            position += 2
            continue
        if character == '"':
            value = _decode_string(text[index + 1 : position])
            if value is not None:
                yield value, position + 1
        position += 1


def _decode_string(inner: str) -> str | None:
    escaped = _escape_interior_quotes(inner)
    for candidate in (inner, escaped, _repair_escapes(escaped), _repair_escapes(inner)):
        try:
            return json.loads('"' + candidate + '"', strict=False)
        except (json.JSONDecodeError, TypeError, RecursionError):
            continue
    return None


def _escape_interior_quotes(inner: str) -> str:
    pieces: list[str] = []
    index = 0
    while index < len(inner):
        character = inner[index]
        if character == "\\" and index + 1 < len(inner):
            pieces.append(inner[index : index + 2])
            index += 2
            continue
        pieces.append('\\"' if character == '"' else character)
        index += 1
    return "".join(pieces)


def _skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


class _Budget:
    """Cap the backtracking search so a pathological reply cannot stall a run."""

    def __init__(self, steps: int) -> None:
        self.steps = steps

    def spend(self) -> bool:
        self.steps -= 1
        return self.steps > 0


_DECODER = json.JSONDecoder(strict=False)
