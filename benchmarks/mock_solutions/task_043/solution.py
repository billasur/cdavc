"""Expand a run length encoded string."""


def decode_rle(text: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(text):
        character = text[index]
        index += 1
        start = index
        while index < len(text) and text[index].isdigit():
            index += 1
        if start == index:
            raise ValueError(f"missing count after {character!r}")
        count = int(text[start:index])
        if count < 1:
            raise ValueError(f"non-positive count for {character!r}")
        result.append(character * count)
    return "".join(result)
