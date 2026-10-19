def longest_common_prefix(words: list[str]) -> str:
    if not words:
        return ""
    prefix = words[0]
    for word in words[1:]:
        limit = min(len(prefix), len(word))
        index = 0
        while index < limit and prefix[index] == word[index]:
            index += 1
        prefix = prefix[:index]
        if not prefix:
            break
    return prefix
