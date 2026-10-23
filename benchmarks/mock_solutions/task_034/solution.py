"""Wrap text into fixed width lines."""


def wrap_text(text: str, width: int) -> list[str]:
    if width < 1:
        raise ValueError("width must be at least 1")
    lines: list[str] = []
    current: list[str] = []
    for word in text.split():
        if not current:
            current = [word]
        elif len(" ".join(current + [word])) <= width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines
