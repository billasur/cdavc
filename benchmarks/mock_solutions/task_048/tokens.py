"""Word bigram helpers."""


def bigrams(text: str) -> list[str]:
    words = text.lower().split()
    return [f"{words[index]} {words[index + 1]}" for index in range(len(words) - 1)]
