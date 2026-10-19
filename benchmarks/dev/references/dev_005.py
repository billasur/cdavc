def count_substring(text, needle):
    if not needle:
        return 0
    return text.count(needle)
