"""Metamorphic property gate for the CD-AVC benchmark corpus.

The properties are frozen in ``benchmarks/properties.json`` and hashed exactly
like the test files, so a property cannot be added after seeing a failure
without that edit becoming visible in the record's ``property_table_hash``.

The oracle here is ours, not the hidden evaluator's: each property is derived
from the task description and its declared invariants.  A failing case is
reported as ``input -> expected, got`` and may therefore be forwarded to a
repair prompt without leaking a held-out assertion.

Run the gate against a candidate::

    python -m cdavc.properties --table benchmarks/properties.json \\
        --task task_006 --seed 0 \\
        --file benchmarks/tasks/task_006/solution.py

The process prints one JSON object on stdout and exits non-zero only when the
candidate cannot be imported or a property raises outside an assertion.
"""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import math
import random
import re
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import parse_qsl, unquote_plus

try:  # ``-m cdavc.properties`` imports the package; a direct run needs the sibling module
    from .mutants import DEFAULT_MUTANTS, MUTANT_TIMEOUT_SECONDS, kill_rate as mutant_kill_rate
except ImportError:  # pragma: no cover - direct script execution
    from mutants import DEFAULT_MUTANTS, MUTANT_TIMEOUT_SECONDS, kill_rate as mutant_kill_rate  # type: ignore[no-redef]

PROPERTY_VERSION = "1"
DEFAULT_TABLE = "benchmarks/properties.json"
DEFAULT_CASES = 16
"""Number of generated cases per property unless the table overrides it."""


class PropertyTableError(RuntimeError):
    """Raised when the frozen property table is malformed."""


@dataclass(frozen=True)
class PropertyFailure:
    """One rejected candidate input, safe to place in a repair prompt."""

    property: str
    arguments: tuple[Any, ...]
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "property": self.property,
            "args": _jsonable(list(self.arguments)),
            "message": self.message,
        }

    def render(self) -> str:
        shown = ", ".join(repr(_jsonable(argument)) for argument in self.arguments)
        return f"{self.property}({shown}): {self.message}"


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


# --------------------------------------------------------------------------
# Generators: each yields argument tuples for one property check.
# Generated values are JSON-safe so a failing case can be replayed verbatim.
# --------------------------------------------------------------------------


def _random_ints(rng: random.Random, *, size: int = 6, low: int = -6, high: int = 6) -> list[int]:
    return [rng.randint(low, high) for _ in range(rng.randint(0, size))]


def _random_text(rng: random.Random, alphabet: str, size: int = 12) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, size)))


def _sorted_ints(rng: random.Random, *, size: int = 6) -> list[int]:
    return sorted(_random_ints(rng, size=size))


def _g_count_vowels(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    alphabet = "aeiouAEIOUyYbcdfgh 1!?"
    for _ in range(count):
        yield (_random_text(rng, alphabet, 14),)


def _g_palindrome(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    alphabet = "abAB1 !,"
    for _ in range(count):
        core = _random_text(rng, alphabet, 6)
        normalized = "".join(character.lower() for character in core if character.isalnum())
        yield (normalized + core + normalized[::-1],)
        yield (_random_text(rng, alphabet, 16),)


def _g_reverse_words(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    words = ("alpha", "beta", "gamma", "delta", "")
    for _ in range(count):
        parts = [rng.choice(words) for _ in range(rng.randint(1, 5))]
        separator = rng.choice([" ", "  ", "\t", " \n "])
        yield (separator.join(parts),)


def _g_run_length(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    for _ in range(count):
        yield ("".join(rng.choice("aabbbc") for _ in range(rng.randint(1, 14))),)


def _g_chunk(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], 1)
    yield ([1, 2, 3], 0)
    yield ([1, 2, 3], -2)
    for _ in range(count):
        yield (_random_ints(rng, size=9), rng.randint(1, 5))


def _g_sorted_pair(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], [])
    yield ([1, 1], [1, 1])
    for _ in range(count):
        yield (_sorted_ints(rng), _sorted_ints(rng))


def _g_rotate(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], 3)
    yield ([1, 2], 0)
    for _ in range(count):
        yield (_random_ints(rng, size=8), rng.randint(-12, 12))


def _g_unique(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    for _ in range(count):
        yield ([rng.choice("abcde") if rng.random() < 0.6 else rng.randint(0, 3) for _ in range(rng.randint(1, 10))],)


def _g_flatten(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    for _ in range(count):
        groups: list[Any] = []
        for _ in range(rng.randint(1, 4)):
            if rng.random() < 0.4:
                groups.append(_random_text(rng, "xyz", 4))
            else:
                groups.append(_random_ints(rng, size=4))
        yield (groups,)


def _g_anagrams(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    bases = ("abc", "foo", "bat", "silent", "listen", "cab", "obf")
    for _ in range(count):
        words = []
        for _ in range(rng.randint(1, 6)):
            base = rng.choice(bases)
            letters = list(base)
            rng.shuffle(letters)
            word = "".join(letters)
            if rng.random() < 0.3:
                word = word.capitalize()
            words.append(word)
        yield (words,)


def _g_top_k(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], 2)
    yield ([1, 2], 0)
    for _ in range(count):
        values = _random_ints(rng, size=10, low=0, high=4)
        yield (values, rng.randint(-1, max(1, len(set(values)) + 1)))


def _g_brackets(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    yield ("([)]",)
    yield (")( ",)
    pairs = (("(", ")"), ("[", "]"), ("{", "}"))
    noise = "abc 12"
    for _ in range(count):
        stack: list[str] = []
        pieces: list[str] = []
        for _ in range(rng.randint(1, 6)):
            if stack and rng.random() < 0.5:
                pieces.append(stack.pop())
            else:
                opening, closing = rng.choice(pairs)
                stack.append(closing)
                pieces.append(opening)
            if rng.random() < 0.3:
                pieces.append(rng.choice(noise))
        pieces.extend(reversed(stack))
        yield ("".join(pieces),)


def _g_camel(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    yield ("A",)
    yield ("HTTPRequest",)
    yield ("already_snake",)
    yield ("getHTTPResponseCode",)
    words = ("parse", "http", "response", "code", "user", "id", "value")
    for _ in range(count):
        parts = [rng.choice(words) for _ in range(rng.randint(1, 4))]
        style = rng.random()
        if style < 0.4:
            name = parts[0] + "".join(part.capitalize() for part in parts[1:])
        elif style < 0.7:
            name = "".join(part.capitalize() for part in parts)
        else:
            name = "_".join(parts)
        yield (name,)


def _g_query(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("",)
    yield ("q=hello%20world&flag=&q=again",)
    keys = ("q", "flag", "page", "tag", "empty")
    values = ("", "a", "hello world", "1", "a&b", "x=y")
    for _ in range(count):
        pairs = []
        for _ in range(rng.randint(1, 5)):
            key = rng.choice(keys)
            value = rng.choice(values)
            pairs.append(f"{key}={unquote_plus(value).replace(' ', '%20').replace('&', '%26')}")
        yield ("&".join(pairs),)


def _g_int_lists(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    yield ([0, 0],)
    yield ([-4, 6],)
    for _ in range(count):
        yield (_random_ints(rng, size=5, low=-24, high=24),)


def _g_int_values(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    for value in (0, 1, 2, 3, 4, 9, 15, 25, 49, 97, 7919, 8000):
        yield (value,)
    for _ in range(count):
        yield (rng.randint(0, 200),)


def _g_index(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], 3)
    yield ([1, 2, 2, 2, 4], 2)
    for _ in range(count):
        values = sorted(rng.randint(0, 5) for _ in range(rng.randint(1, 9)))
        yield (values, rng.randint(-1, 6))


def _g_words(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    yield (["dog", "racecar"],)
    yield (["flower", "flow", "flight"],)
    for _ in range(count):
        base = _random_text(rng, "abc", 4)
        words = [base + _random_text(rng, "abc", 3) for _ in range(rng.randint(1, 4))]
        yield (words,)


def _g_string_pairs(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ("", "abc")
    yield ("kitten", "sitting")
    for _ in range(count):
        yield (_random_text(rng, "abc", 7), _random_text(rng, "abc", 7))


def _g_rect_matrices(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    for _ in range(count):
        rows = rng.randint(1, 4)
        columns = rng.randint(1, 4)
        yield ([[rng.randint(-9, 9) for _ in range(columns)] for _ in range(rows)],)


def _g_matrices(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    yield ([[1], [2, 3]],)
    for _ in range(count):
        rows = rng.randint(1, 4)
        columns = rng.randint(1, 4)
        yield ([[rng.randint(-9, 9) for _ in range(columns)] for _ in range(rows)],)


def _g_matrix_pairs(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([[1, 2]], [[1, 2]])
    for _ in range(count):
        inner = rng.randint(1, 3)
        rows = rng.randint(1, 3)
        columns = rng.randint(1, 3)
        left = [[rng.randint(-4, 4) for _ in range(inner)] for _ in range(rows)]
        right = [[rng.randint(-4, 4) for _ in range(columns)] for _ in range(inner)]
        yield (left, right)


def _g_intervals(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([],)
    yield ([[5, 7], [1, 2], [2, 5], [10, 10]],)
    for _ in range(count):
        intervals = []
        for _ in range(rng.randint(1, 6)):
            start = rng.randint(0, 12)
            intervals.append([start, start + rng.randint(0, 4)])
        yield (intervals,)


def _rpn_divides_by_zero(tokens: Sequence[str]) -> bool:
    """Simulate a well-formed expression and report a zero divisor.

    Replacing literal ``"0"`` tokens is not enough: an intermediate result can
    still be zero, and the oracle would then raise instead of the candidate.
    Such a case is a separate contract (``ValueError``), so the generator
    skips it rather than charging the candidate for our own division.
    """

    stack: list[int] = []
    for token in tokens:
        if token not in {"+", "-", "*", "/"}:
            stack.append(int(token))
            continue
        if len(stack) < 2:
            # Malformed expressions are the candidate's contract to enforce,
            # not a division hazard for the generator.
            return False
        right = stack.pop()
        left = stack.pop()
        if token == "+":
            stack.append(left + right)
        elif token == "-":
            stack.append(left - right)
        elif token == "*":
            stack.append(left * right)
        else:
            if right == 0:
                return True
            stack.append(math.trunc(left / right))
    return False


def _g_rpn(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield (["5", "2", "/"],)
    yield (["-7", "2", "/"],)
    yield (["2", "+"],)
    emitted = 0
    attempts = 0
    while emitted < count and attempts < count * 4:
        attempts += 1
        tokens: list[str] = [str(rng.randint(-9, 9))]
        depth = 1
        for _ in range(rng.randint(1, 5)):
            if depth >= 2 and rng.random() < 0.5:
                tokens.append(rng.choice(["+", "-", "*", "/"]))
                depth -= 1
            else:
                tokens.append(str(rng.randint(-9, 9)))
                depth += 1
        while depth > 1:
            tokens.append(rng.choice(["+", "-", "*", "/"]))
            depth -= 1
        if _rpn_divides_by_zero(tokens):
            continue
        emitted += 1
        yield (tokens,)


def _g_durations(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    for value in (0, 1, 59, 60, 61, 3599, 3600, 3661, 86400, 90061, 172800):
        yield (value,)
    yield (-1,)
    for _ in range(count):
        yield (rng.randint(0, 400000),)


def _g_records(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    yield ([], "score")
    yield ([{"name": "first", "score": 2}, {"name": "second", "score": 1}, {"name": "third", "score": 2}], "score")
    for _ in range(count):
        records = [{"name": f"n{index}", "score": rng.randint(0, 3)} for index in range(rng.randint(1, 7))]
        yield (records, "score")


def _g_roman_parse_cases(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    del rng, count
    for numeral, _value in entry["corpus"]:
        yield (numeral,)
    for numeral in entry["invalid"]:
        yield (numeral,)


def _g_roman_format_cases(entry: Mapping[str, Any], rng: random.Random, count: int) -> Iterator[tuple[Any, ...]]:
    del rng, count
    for _numeral, value in entry["corpus"]:
        yield (value,)
    for value in entry.get("out_of_range", (0, 4000, -1)):
        yield (value,)


# --------------------------------------------------------------------------
# Checks: each asserts one property of the candidate's output.
# --------------------------------------------------------------------------


def _c_count_vowels(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (text,) = arguments
    expected = sum(character.lower() in "aeiou" for character in text)
    result = module.count_vowels(text)
    assert isinstance(result, int) and not isinstance(result, bool), f"expected an int, got {type(result).__name__}"
    assert result == expected, f"expected {expected}, got {result}"


def _c_palindrome(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (text,) = arguments
    normalized = "".join(character.lower() for character in text if character.isalnum())
    expected = normalized == normalized[::-1]
    result = module.is_palindrome(text)
    assert isinstance(result, bool), f"expected a bool, got {type(result).__name__}"
    assert result == expected, f"expected {expected}, got {result}"


def _c_reverse_words(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (text,) = arguments
    result = module.reverse_words(text)
    assert isinstance(result, str), f"expected a str, got {type(result).__name__}"
    expected = " ".join(reversed(text.split()))
    assert result == expected, f"expected {expected!r}, got {result!r}"


_RUN = re.compile(r"(.)(\d+)")


def _c_run_length(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (text,) = arguments
    result = module.run_length_encode(text)
    assert isinstance(result, str), f"expected a str, got {type(result).__name__}"
    if not text:
        assert result == "", f"expected '' for empty input, got {result!r}"
        return
    position = 0
    decoded: list[str] = []
    previous = None
    while position < len(result):
        match = _RUN.match(result, position)
        assert match is not None, f"unparseable run at offset {position}: {result!r}"
        character, count = match.group(1), int(match.group(2))
        assert count >= 1, f"run count must be positive, got {count}"
        assert character != previous, f"adjacent runs for {character!r} were not joined"
        decoded.append(character * count)
        previous = character
        position = match.end()
    assert "".join(decoded) == text, f"decoded {''.join(decoded)!r} != input {text!r}"


def _c_chunk(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    items, size = arguments
    if size <= 0:
        try:
            module.chunk(items, size)
        except ValueError:
            return
        raise AssertionError(f"expected ValueError for size={size}")
    expected = list(items)
    result = module.chunk(items, size)
    assert isinstance(result, list) and all(isinstance(part, list) for part in result), "expected a list of lists"
    assert [item for part in result for item in part] == expected, "chunks do not partition the input"
    assert all(len(part) == size for part in result[:-1]) if result else True, "only the last chunk may be short"
    assert all(part for part in result), "chunks must not be empty"


def _c_merge_sorted(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    left, right = arguments
    expected = sorted(list(left) + list(right))
    result = module.merge_sorted(left, right)
    assert isinstance(result, list), f"expected a list, got {type(result).__name__}"
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _rotate_reference(values: Sequence[Any], steps: int) -> list[Any]:
    if not values:
        return []
    offset = steps % len(values)
    return list(values[-offset:]) + list(values[:-offset]) if offset else list(values)


def _c_rotate(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    values, steps = arguments
    expected = _rotate_reference(values, steps)
    result = module.rotate(values, steps)
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _c_unique(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (values,) = arguments
    expected: list[Any] = []
    for value in values:
        if value not in expected:
            expected.append(value)
    result = module.unique_preserve(values)
    assert result == expected, f"expected {expected!r}, got {result!r}"
    assert module.unique_preserve(list(result)) == result, "unique_preserve is not idempotent"


def _c_flatten(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (groups,) = arguments
    expected = [item for group in groups for item in group]
    result = module.flatten_once(groups)
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _c_anagrams(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (words,) = arguments
    result = module.group_anagrams(words)
    assert isinstance(result, dict), f"expected a dict, got {type(result).__name__}"
    flattened = [word for group in result.values() for word in group]
    assert sorted(flattened) == sorted(words), f"grouped words {flattened!r} are not the input words {list(words)!r}"
    assert len(flattened) == len(words), f"grouped words {flattened!r} repeat or drop an input word"
    for signature, group in result.items():
        assert group, f"group {signature!r} is empty"
        for word in group:
            assert "".join(sorted(word.lower())) == signature, f"{word!r} does not belong to key {signature!r}"


def _c_top_k(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    values, k = arguments
    expected_order = list(values)
    result = module.top_k_frequent(values, k)
    if k <= 0:
        assert result == [], f"expected [] for k={k}, got {result!r}"
        return
    counts: dict[Any, int] = {}
    first: dict[Any, int] = {}
    for index, value in enumerate(values):
        counts[value] = counts.get(value, 0) + 1
        first.setdefault(value, index)
    expected = sorted(counts, key=lambda value: (-counts[value], first[value]))[:k]
    assert result == expected, f"expected {expected!r}, got {result!r}"
    assert list(values) == expected_order, "input order changed"


def _c_brackets(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (text,) = arguments
    result = module.balanced_brackets(text)
    assert isinstance(result, bool), f"expected a bool, got {type(result).__name__}"
    stack: list[str] = []
    matching = {")": "(", "]": "[", "}": "{"}
    for character in text:
        if character in "([{":
            stack.append(character)
        elif character in matching:
            if not stack or stack.pop() != matching[character]:
                stack.append("!")
                break
    assert result == (not stack), f"expected {not stack}, got {result} for {text!r}"


def _c_camel(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (name,) = arguments
    result = module.camel_to_snake(name)
    assert isinstance(result, str), f"expected a str, got {type(result).__name__}"
    assert result == result.lower(), f"result {result!r} is not lowercase"
    assert "__" not in result and not result.startswith("_") and not result.endswith("_"), f"separators in {result!r} are not normalized"
    assert result.replace("_", "") == name.replace("_", "").lower(), f"{result!r} does not preserve the letters of {name!r}"
    assert module.camel_to_snake(result) == result, "camel_to_snake is not idempotent"


def _c_query(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (query,) = arguments
    result = module.parse_query(query)
    expected: dict[str, list[str]] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        expected.setdefault(key, []).append(value)
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _c_roman_parse(module: ModuleType, arguments: tuple[Any, ...], entry: Mapping[str, Any]) -> None:
    (numeral,) = arguments
    corpus = dict(entry["corpus"])
    invalid = tuple(entry["invalid"])
    if numeral in corpus:
        expected = corpus[numeral]
        result = module.roman_to_int(numeral)
        assert result == expected, f"expected {expected}, got {result} for {numeral!r}"
        return
    assert numeral in invalid, f"property table produced an unlabelled case {numeral!r}"
    try:
        module.roman_to_int(numeral)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for non-canonical numeral {numeral!r}")


def _c_roman_format(module: ModuleType, arguments: tuple[Any, ...], entry: Mapping[str, Any]) -> None:
    (value,) = arguments
    numerals = {number: numeral for numeral, number in entry["corpus"]}
    if value in numerals:
        expected = numerals[value]
        result = module.int_to_roman(value)
        assert result == expected, f"expected {expected!r}, got {result!r} for {value}"
        return
    try:
        module.int_to_roman(value)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for out-of-range value {value}")


def _c_gcd(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (values,) = arguments
    if not values:
        try:
            module.gcd_many([])
        except ValueError:
            return
        raise AssertionError("expected ValueError for an empty list")
    expected = 0
    for value in values:
        expected = math.gcd(expected, value)
    result = module.gcd_many(list(values))
    assert result == expected, f"expected {expected}, got {result}"
    assert result >= 0, f"result {result} is negative"


def _c_lcm(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (values,) = arguments
    if not values:
        try:
            module.lcm_many([])
        except ValueError:
            return
        raise AssertionError("expected ValueError for an empty list")
    expected = 1
    for value in values:
        expected = math.lcm(expected, value)
    result = module.lcm_many(list(values))
    assert result == expected, f"expected {expected}, got {result}"
    assert result >= 0, f"result {result} is negative"


def _prime_reference(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _c_prime(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (value,) = arguments
    result = module.is_prime(value)
    assert isinstance(result, bool), f"expected a bool, got {type(result).__name__}"
    expected = _prime_reference(value)
    assert result == expected, f"expected {expected} for {value}, got {result}"


def _fibonacci_reference(index: int) -> int:
    previous, current = 0, 1
    for _ in range(index):
        previous, current = current, previous + current
    return previous


def _c_fibonacci(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (index,) = arguments
    expected = _fibonacci_reference(index)
    result = module.fibonacci(index)
    assert result == expected, f"expected {expected} for {index}, got {result}"


def _c_binary_search(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    values, target = arguments
    expected_order = list(values)
    result = module.binary_search(values, target)
    try:
        expected = list(values).index(target)
    except ValueError:
        expected = -1
    assert result == expected, f"expected {expected} for {target} in {values!r}, got {result}"
    assert list(values) == expected_order, "input order changed" 


def _c_lcp(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (words,) = arguments
    expected_order = list(words)
    result = module.longest_common_prefix(words)
    if not words:
        expected = ""
    else:
        expected = words[0]
        for word in words[1:]:
            while not word.startswith(expected):
                expected = expected[:-1]
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _c_levenshtein(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    left, right = arguments
    distance = module.levenshtein_distance(left, right)
    assert isinstance(distance, int) and not isinstance(distance, bool), f"expected an int, got {type(distance).__name__}"
    assert distance == module.levenshtein_distance(right, left), "distance is not symmetric"
    assert distance == 0 if left == right else distance > 0, "distance is zero only for equal strings"
    if abs(len(left) - len(right)) > distance:
        raise AssertionError(f"distance {distance} is below the length difference of {left!r} and {right!r}")
    if distance > max(len(left), len(right)):
        raise AssertionError(f"distance {distance} exceeds max(len(left), len(right))")


def _transpose_reference(matrix: Sequence[Sequence[Any]]) -> list[list[Any]]:
    if not matrix:
        return []
    return [[row[column] for row in matrix] for column in range(len(matrix[0]))]


def _c_transpose(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (matrix,) = arguments
    width = len(matrix[0]) if matrix else 0
    if any(len(row) != width for row in matrix):
        try:
            module.transpose(matrix)
        except ValueError:
            return
        raise AssertionError("expected ValueError for a ragged matrix")
    expected = _transpose_reference(matrix)
    original = [list(row) for row in matrix]
    result = module.transpose(matrix)
    assert result == expected, f"expected {expected!r}, got {result!r}"
    assert module.transpose(result) == original, "transpose is not an involution"


def _c_spiral(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (matrix,) = arguments
    expected = sorted(value for row in matrix for value in row)
    result = module.spiral_order(matrix)
    assert sorted(result) == expected, f"spiral order is not a permutation of the matrix: {result!r}"


def _c_matrix_multiply(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    left, right = arguments
    incompatible = not left or not right or len(left[0]) != len(right)
    ragged = any(len(row) != len(left[0]) for row in left) or any(len(row) != len(right[0]) for row in right)
    if incompatible or ragged:
        try:
            module.matrix_multiply(left, right)
        except ValueError:
            return
        raise AssertionError("expected ValueError for incompatible matrices")
    expected = [
        [sum(left[row][inner] * right[inner][column] for inner in range(len(right))) for column in range(len(right[0]))]
        for row in range(len(left))
    ]
    result = module.matrix_multiply(left, right)
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _merge_intervals_reference(intervals: Sequence[Sequence[int]]) -> list[list[int]]:
    ordered = sorted((list(interval) for interval in intervals), key=lambda interval: interval[0])
    result: list[list[int]] = []
    for start, end in ordered:
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def _c_intervals(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (intervals,) = arguments
    expected = _merge_intervals_reference(intervals)
    result = module.merge_intervals(intervals)
    assert result == expected, f"expected {expected!r}, got {result!r}"


def _rpn_reference(tokens: Sequence[str]) -> int:
    stack: list[int] = []
    for token in tokens:
        if token in {"+", "-", "*", "/"}:
            right = stack.pop()
            left = stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            elif token == "*":
                stack.append(left * right)
            else:
                stack.append(math.trunc(left / right))
        else:
            stack.append(int(token))
    return stack[0]


def _c_rpn(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (tokens,) = arguments
    depth = 0
    malformed = False
    for token in tokens:
        if token in {"+", "-", "*", "/"}:
            if depth < 2:
                malformed = True
                break
            depth -= 1
        else:
            depth += 1
    if malformed or depth != 1:
        try:
            module.evaluate_rpn(list(tokens))
        except ValueError:
            return
        raise AssertionError(f"expected ValueError for malformed expression {tokens!r}")
    expected = _rpn_reference(tokens)
    result = module.evaluate_rpn(list(tokens))
    assert result == expected, f"expected {expected} for {tokens!r}, got {result}"


def _format_duration_reference(seconds: int) -> str:
    if seconds == 0:
        return "0s"
    parts = []
    for amount, suffix in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s")):
        count, seconds = divmod(seconds, amount)
        if count:
            parts.append(f"{count}{suffix}")
    return " ".join(parts)


_UNIT = re.compile(r"(\d+)([dhms])")


def _c_duration(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    (seconds,) = arguments
    if seconds < 0:
        try:
            module.format_duration(seconds)
        except ValueError:
            return
        raise AssertionError(f"expected ValueError for {seconds}")
    result = module.format_duration(seconds)
    expected = _format_duration_reference(seconds)
    assert result == expected, f"expected {expected!r}, got {result!r} for {seconds}"


def _c_records(module: ModuleType, arguments: tuple[Any, ...]) -> None:
    records, key = arguments
    expected = sorted(records, key=lambda record: record[key])
    result = module.stable_sort_records(records, key)
    assert result == expected, f"expected {expected!r}, got {result!r}"


# --------------------------------------------------------------------------
# Dev-corpus differential property.
#
# Iteration happens on ``benchmarks/dev``, whose tasks are checked by
# comparing the candidate against a frozen reference implementation over
# generated inputs.  The reference is a repository file committed with the dev
# corpus, so this stays table-driven and is hashed with the rest of it.  The
# held-out table does not use this check.
# --------------------------------------------------------------------------

_REFERENCE_CACHE: dict[str, ModuleType] = {}


def _load_reference(path: str) -> ModuleType:
    module = _REFERENCE_CACHE.get(path)
    if module is None:
        location = Path(path)
        if not location.is_file():
            raise PropertyTableError(f"dev reference does not exist: {location}")
        spec = importlib.util.spec_from_file_location(
            f"cdavc_dev_reference_{len(_REFERENCE_CACHE)}", location
        )
        if spec is None or spec.loader is None:
            raise PropertyTableError(f"cannot import dev reference: {location}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _REFERENCE_CACHE[path] = module
    return module


_DEV_WORDS = ("alpha", "beta", "gamma", "delta", "echo", "foxtrot", "golf", "hotel")
_DEV_IPS = (
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
    "256.1.1.1",
    "01.2.3.4",
    "1.2.3",
    "1.2.3.4.5",
    "a.b.c.d",
    "192.168.0.10",
    "",
)
_DEV_DAYS = ("Monday", "tuesday", "WEDNESDAY", "Thursday", "friday", "Saturday", "sunday")
_DEV_CSVS = ("", "1", "1, 2,,3", " 4 ,5 ", "1,a", "-2,-3", "7,8,9")
_DEV_CSVS_OK = ("", "1", "1, 2,,3", " 4 ,5 ", "-2,-3", "7,8,9")

def _shape_same_pair_lists(rng: random.Random) -> tuple[Any, ...]:
    size = rng.randint(0, 5)
    return (
        [rng.randint(-9, 9) for _ in range(size)],
        [rng.randint(-9, 9) for _ in range(size)],
    )


_DEV_SHAPES: dict[str, Callable[[random.Random], tuple[Any, ...]]] = {
    "int": lambda rng: (rng.randint(0, 60),),
    "int2": lambda rng: (rng.randint(-20, 20), rng.randint(-20, 20)),
    "int3": lambda rng: (rng.randint(0, 20), rng.randint(0, 6), rng.randint(-2, 22)),
    "intlist": lambda rng: ([rng.randint(-9, 9) for _ in range(rng.randint(0, 7))],),
    "poslist": lambda rng: ([rng.randint(1, 12) for _ in range(rng.randint(1, 6))],),
    "numlist": lambda rng: ([round(rng.uniform(-10, 10), 3) for _ in range(rng.randint(1, 6))],),
    "text": lambda rng: (" ".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(0, 5))),),
    "text2": lambda rng: (
        " ".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(1, 4))),
        " ".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(1, 4))),
    ),
    "text_int": lambda rng: (
        " ".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(1, 4))),
        rng.randint(0, 24),
    ),
    "records": lambda rng: (
        [
            {"name": rng.choice(_DEV_WORDS), "score": rng.randint(0, 9)}
            for _ in range(rng.randint(1, 5))
        ],
    ),
    "mapping": lambda rng: (
        {rng.choice(_DEV_WORDS): rng.choice(_DEV_WORDS) for _ in range(rng.randint(1, 4))},
    ),
    "smallint": lambda rng: (rng.randint(0, 18),),
    "int_signed": lambda rng: (rng.randint(-50, 50),),
    "int2nonneg": lambda rng: (rng.randint(0, 20), rng.randint(0, 20)),
    "clamp": lambda rng: (
        rng.randint(-50, 50),
        (low := rng.randint(-20, 20)),
        low + rng.randint(0, 20),
    ),
    "pair_lists": lambda rng: (
        [rng.randint(-9, 9) for _ in range(rng.randint(0, 5))],
        [rng.randint(-9, 9) for _ in range(rng.randint(0, 5))],
    ),
    "same_pair_lists": _shape_same_pair_lists,
    "records_int": lambda rng: (
        [
            {"name": rng.choice(_DEV_WORDS), "score": rng.randint(0, 9)}
            for _ in range(rng.randint(0, 5))
        ],
    ),
    "records_min": lambda rng: (
        [
            {"name": rng.choice(_DEV_WORDS), "score": rng.randint(0, 9)}
            for _ in range(rng.randint(0, 5))
        ],
        rng.randint(0, 9),
    ),
    "list_width": lambda rng: (
        [rng.randint(0, 30) for _ in range(rng.randint(0, 6))],
        rng.randint(1, 5),
    ),
    "binary": lambda rng: ("".join(rng.choice("01") for _ in range(rng.randint(1, 8))),),
    "hexcolor": lambda rng: ("#" + "".join(rng.choice("0123456789abcdef") for _ in range(6)),),
    "rgb": lambda rng: (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)),
    "ipv4ish": lambda rng: (rng.choice(_DEV_IPS),),
    "weekday": lambda rng: (rng.choice(_DEV_DAYS),),
    "int_csv": lambda rng: (rng.choice(_DEV_CSVS),),
    "int_csv_ok": lambda rng: (rng.choice(_DEV_CSVS_OK),),
    "text_width": lambda rng: (
        " ".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(0, 5))),
        rng.randint(4, 18),
    ),
    "snake": lambda rng: (
        "_".join(rng.choice(_DEV_WORDS) for _ in range(rng.randint(0, 4))),
    ),
}


def _g_dev_reference(
    entry: Mapping[str, Any], rng: random.Random, count: int
) -> Iterator[tuple[Any, ...]]:
    shape = _DEV_SHAPES[str(entry.get("shape", "int"))]
    for _ in range(count):
        yield shape(rng)


def _check_dev_reference(
    module: ModuleType, arguments: tuple[Any, ...], entry: Mapping[str, Any]
) -> None:
    symbol = str(entry["symbol"])
    candidate = getattr(module, symbol, None)
    if not callable(candidate):
        raise AssertionError(f"{symbol} is not callable")
    reference = getattr(_load_reference(str(entry["reference"])), symbol)
    expected = reference(*copy.deepcopy(arguments))
    actual = candidate(*copy.deepcopy(arguments))
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


CHECKS: dict[str, Callable[..., None]] = {
    "count_vowels_identity": _c_count_vowels,
    "palindrome_normal_form": _c_palindrome,
    "reverse_words_reference": _c_reverse_words,
    "run_length_round_trip": _c_run_length,
    "chunk_partition": _c_chunk,
    "merge_sorted_multiset": _c_merge_sorted,
    "rotate_reference": _c_rotate,
    "unique_first_occurrence": _c_unique,
    "flatten_once_concatenation": _c_flatten,
    "group_anagrams_signature": _c_anagrams,
    "top_k_order": _c_top_k,
    "balanced_brackets_reference": _c_brackets,
    "camel_to_snake_normal_form": _c_camel,
    "parse_query_reference": _c_query,
    "roman_parse_corpus": _c_roman_parse,
    "roman_format_corpus": _c_roman_format,
    "gcd_reference": _c_gcd,
    "lcm_reference": _c_lcm,
    "prime_reference": _c_prime,
    "fibonacci_reference": _c_fibonacci,
    "binary_search_first_index": _c_binary_search,
    "longest_common_prefix_reference": _c_lcp,
    "levenshtein_metric": _c_levenshtein,
    "transpose_involution": _c_transpose,
    "spiral_permutation": _c_spiral,
    "matrix_multiply_reference": _c_matrix_multiply,
    "merge_intervals_reference": _c_intervals,
    "rpn_reference": _c_rpn,
    "format_duration_reference": _c_duration,
    "stable_sort_reference": _c_records,
    "dev_reference_matches": _check_dev_reference,
}

GENERATORS: dict[str, Callable[[Mapping[str, Any], random.Random, int], Iterator[tuple[Any, ...]]]] = {
    "count_vowels_identity": _g_count_vowels,
    "palindrome_normal_form": _g_palindrome,
    "reverse_words_reference": _g_reverse_words,
    "run_length_round_trip": _g_run_length,
    "chunk_partition": _g_chunk,
    "merge_sorted_multiset": _g_sorted_pair,
    "rotate_reference": _g_rotate,
    "unique_first_occurrence": _g_unique,
    "flatten_once_concatenation": _g_flatten,
    "group_anagrams_signature": _g_anagrams,
    "top_k_order": _g_top_k,
    "balanced_brackets_reference": _g_brackets,
    "camel_to_snake_normal_form": _g_camel,
    "parse_query_reference": _g_query,
    "roman_parse_corpus": _g_roman_parse_cases,
    "roman_format_corpus": _g_roman_format_cases,
    "gcd_reference": _g_int_lists,
    "lcm_reference": _g_int_lists,
    "prime_reference": _g_int_values,
    "fibonacci_reference": _g_int_values,
    "binary_search_first_index": _g_index,
    "longest_common_prefix_reference": _g_words,
    "levenshtein_metric": _g_string_pairs,
    "transpose_involution": _g_matrices,
    "spiral_permutation": _g_rect_matrices,
    "matrix_multiply_reference": _g_matrix_pairs,
    "merge_intervals_reference": _g_intervals,
    "rpn_reference": _g_rpn,
    "format_duration_reference": _g_durations,
    "stable_sort_reference": _g_records,
    "dev_reference_matches": _g_dev_reference,
}

NEEDS_ENTRY = {"roman_parse_corpus", "roman_format_corpus", "dev_reference_matches"}

REQUIRES_CORPUS = {"roman_parse_corpus", "roman_format_corpus"}


# --------------------------------------------------------------------------
# Table loading and execution
# --------------------------------------------------------------------------


def load_table(path: Path | str) -> dict[str, Any]:
    """Read and validate the frozen property table."""

    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, Mapping) or not isinstance(payload.get("tasks"), Mapping):
        raise PropertyTableError("property table must contain a tasks object")
    tasks = payload["tasks"]
    for task_id, entries in tasks.items():
        if not isinstance(entries, list):
            raise PropertyTableError(f"properties for {task_id} must be a list")
        for entry in entries:
            if not isinstance(entry, Mapping) or entry.get("property") not in CHECKS:
                raise PropertyTableError(f"unknown property in {task_id}: {entry!r}")
            if entry["property"] in REQUIRES_CORPUS and "corpus" not in entry:
                raise PropertyTableError(f"{entry['property']} requires a frozen corpus in {task_id}")
            if entry["property"] == "dev_reference_matches" and not (
                isinstance(entry.get("symbol"), str) and isinstance(entry.get("reference"), str)
            ):
                raise PropertyTableError(
                    f"dev_reference_matches requires symbol and reference in {task_id}"
                )
    return dict(tasks)


def entries_for(table: Mapping[str, Any], task_id: str) -> list[dict[str, Any]]:
    return list(table.get(task_id, ()))


def _check(module: ModuleType, entry: Mapping[str, Any], arguments: tuple[Any, ...]) -> None:
    name = entry["property"]
    check = CHECKS[name]
    if name in NEEDS_ENTRY:
        check(module, arguments, entry)
    else:
        check(module, arguments)


def run_property(
    module: ModuleType,
    entry: Mapping[str, Any],
    *,
    seed: int,
    count: int | None = None,
) -> tuple[int, list[PropertyFailure]]:
    """Run one table entry and return (cases executed, failures)."""

    name = entry["property"]
    generator = GENERATORS[name]
    rng = random.Random(f"{seed}:{name}")
    limit = int(entry.get("cases", DEFAULT_CASES))
    if count is not None:
        limit = count
    executed = 0
    failures: list[PropertyFailure] = []
    for arguments in generator(entry, rng, limit):
        if not isinstance(arguments, tuple):
            arguments = tuple(arguments)
        executed += 1
        snapshot = copy.deepcopy(arguments)
        try:
            _check(module, entry, arguments)
        except AssertionError as exc:
            failures.append(PropertyFailure(name, arguments, str(exc) or "property failed"))
            continue
        except Exception as exc:  # a candidate that raises has failed the property
            failures.append(PropertyFailure(name, arguments, f"raised {type(exc).__name__}: {exc}"))
            continue
        if entry.get("pure"):
            if arguments != snapshot:
                failures.append(PropertyFailure(name, arguments, "mutated its arguments"))
    return executed, failures


def replay_case(module: ModuleType, entry: Mapping[str, Any], arguments: Sequence[Any]) -> PropertyFailure | None:
    """Re-run one previously failing input; return a failure when it regressed."""

    values = tuple(arguments)
    try:
        _check(module, entry, values)
    except AssertionError as exc:
        return PropertyFailure(entry["property"], values, str(exc) or "property failed")
    except Exception as exc:  # noqa: BLE001 - replay reports candidate exceptions as data
        return PropertyFailure(entry["property"], values, f"raised {type(exc).__name__}: {exc}")
    return None


def load_module(paths: Iterable[Path | str]) -> ModuleType:
    """Import each implementation file into one namespace."""

    module = ModuleType("cdavc_property_candidate")
    for index, path in enumerate(paths):
        location = Path(path)
        spec = importlib.util.spec_from_file_location(f"cdavc_property_candidate_{index}", location)
        if spec is None or spec.loader is None:
            raise PropertyTableError(f"cannot import candidate file: {location}")
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        for attribute in dir(loaded):
            if not attribute.startswith("_"):
                setattr(module, attribute, getattr(loaded, attribute))
    return module


def run_table(
    module: ModuleType,
    entries: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    replay: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run every table entry plus any remembered failing inputs."""

    failures: list[PropertyFailure] = []
    executed = 0
    by_name = {entry["property"]: entry for entry in entries}
    for item in replay:
        entry = by_name.get(item.get("property", ""))
        if entry is None:
            continue
        failure = replay_case(module, entry, item.get("args", ()))
        if failure is not None:
            failures.append(failure)
    for entry in entries:
        count, found = run_property(module, entry, seed=seed)
        executed += count
        failures.extend(found)
    return {
        "ok": not failures,
        "checked": executed,
        "replayed": len(replay),
        "failures": [failure.as_dict() for failure in failures],
    }


def probe(
    *,
    table_path: Path | str,
    task_id: str,
    files: Sequence[Path | str],
    seed: int,
    replay_path: Path | str | None = None,
    mutants: int = 0,
    mutant_timeout: float = MUTANT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    table = load_table(table_path)
    entries = entries_for(table, task_id)
    if not entries:
        return {"ok": True, "checked": 0, "replayed": 0, "failures": []}
    replay: list[Mapping[str, Any]] = []
    if replay_path is not None:
        replay = json.loads(Path(replay_path).read_text())
    module = load_module(files)
    result = run_table(module, entries, seed=seed, replay=replay)
    if mutants:
        # The kill rate is a measurement of the gate, not part of it.  It is
        # computed only after the verdict and can never reject a candidate.
        try:
            result["mutants"] = mutant_kill_rate(
                [Path(path).read_text() for path in files],
                entries,
                run_table=run_table,
                seed=seed,
                limit=mutants,
                timeout=mutant_timeout,
            )
        except Exception as exc:  # noqa: BLE001 - a metric failure is not a verdict
            result["mutants"] = {
                "generated": 0,
                "killed": 0,
                "kill_rate": None,
                "error": type(exc).__name__,
            }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CD-AVC metamorphic property gate")
    parser.add_argument("--table", type=Path, default=Path(DEFAULT_TABLE))
    parser.add_argument("--task", required=True)
    parser.add_argument("--file", action="append", type=Path, default=[], help="candidate implementation file; may be repeated")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--replay", type=Path, default=None, help="JSON list of previously failing cases")
    parser.add_argument("--mutants", type=int, default=0, help="also measure mutation kill rate with N mutants")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        result = probe(
            table_path=arguments.table,
            task_id=arguments.task,
            files=arguments.file,
            seed=arguments.seed,
            replay_path=arguments.replay,
            mutants=arguments.mutants,
        )
    except (OSError, ValueError, PropertyTableError) as exc:
        print(f"property gate could not run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


def parse_failures(output: str) -> list[dict[str, Any]]:
    """Extract the failure list from a probe run that exited non-zero."""

    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and isinstance(payload.get("failures"), list):
            return list(payload["failures"])
    return []


def parse_ast_imports(tree: ast.AST) -> set[str]:
    """Return the top-level module names imported by a parsed candidate."""

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def non_stdlib_imports(tree: ast.AST, allowed: Sequence[str] = ()) -> list[str]:
    """Return imported modules outside the standard library, sorted."""

    standard = set(sys.stdlib_module_names) | set(allowed)
    return sorted(name for name in parse_ast_imports(tree) if name not in standard)


__all__ = [
    "PROPERTY_VERSION",
    "PropertyFailure",
    "PropertyTableError",
    "entries_for",
    "load_module",
    "load_table",
    "main",
    "non_stdlib_imports",
    "parse_failures",
    "probe",
    "replay_case",
    "run_property",
    "run_table",
]


if __name__ == "__main__":
    raise SystemExit(main())
