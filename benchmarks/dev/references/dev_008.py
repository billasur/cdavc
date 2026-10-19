def is_anagram(a, b):
    def normalise(text):
        return sorted(ch.lower() for ch in text if ch.isalnum())

    return normalise(a) == normalise(b)
