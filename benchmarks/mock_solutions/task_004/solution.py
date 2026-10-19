def run_length_encode(text: str) -> str:
    if not text:
        return ""
    parts = []
    start = 0
    for index in range(1, len(text) + 1):
        if index == len(text) or text[index] != text[start]:
            parts.append(text[start] + str(index - start))
            start = index
    return "".join(parts)
