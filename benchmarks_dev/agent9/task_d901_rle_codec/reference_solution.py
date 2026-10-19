"""Run-length encode/decode with a canonical counted format."""


def rle_encode(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    out = []
    i = 0
    while i < len(text):
        j = i
        while j < len(text) and text[j] == text[i]:
            j += 1
        out.append(str(j - i))
        out.append(":")
        out.append(text[i])
        i = j
    return "".join(out)


def rle_decode(data: str) -> str:
    if not isinstance(data, str):
        raise TypeError("data must be str")
    out = []
    i = 0
    while i < len(data):
        if not data[i].isdigit():
            raise ValueError(f"expected digit at position {i}")
        j = i
        while j < len(data) and data[j].isdigit():
            j += 1
        count = int(data[i:j])
        if count < 1:
            raise ValueError("count must be >= 1")
        if j >= len(data) or data[j] != ":":
            raise ValueError("count with no ':' separator")
        if j + 1 >= len(data):
            raise ValueError("count and ':' with no following character")
        out.append(data[j + 1] * count)
        i = j + 2
    return "".join(out)
