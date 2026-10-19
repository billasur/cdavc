def group_anagrams(words: list[str]) -> dict[str, list[str]]:
    result = {}
    for word in words:
        signature = "".join(sorted(word.lower()))
        result.setdefault(signature, []).append(word)
    return result
