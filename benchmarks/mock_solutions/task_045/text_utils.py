"""Whitespace helpers shared by the summary code."""


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def word_count(text: str) -> int:
    normalized = normalize_whitespace(text)
    return len(normalized.split()) if normalized else 0
