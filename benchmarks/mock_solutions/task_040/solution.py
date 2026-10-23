"""Rank the words of a text by frequency."""

import re

_WORD = re.compile(r"[a-z0-9]+")


def top_words(text: str, k: int) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for word in _WORD.findall(text.lower()):
        counts[word] = counts.get(word, 0) + 1
    if k <= 0:
        return []
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:k]
