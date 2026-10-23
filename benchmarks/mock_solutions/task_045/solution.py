"""Summarise a text to a word budget."""

from text_utils import normalize_whitespace, word_count


def summarize(text: str, limit: int) -> str:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    normalized = normalize_whitespace(text)
    if word_count(normalized) <= limit:
        return normalized
    return " ".join(normalized.split()[:limit]) + " ..."
