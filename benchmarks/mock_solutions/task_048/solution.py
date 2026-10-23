"""Jaccard similarity of word bigram sets."""

from tokens import bigrams


def jaccard(left: str, right: str) -> float:
    first = set(bigrams(left))
    second = set(bigrams(right))
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0
    return round(len(first & second) / len(first | second), 3)
