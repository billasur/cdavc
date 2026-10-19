def binary_to_int(text):
    if not text or any(ch not in "01" for ch in text):
        raise ValueError("not a binary string")
    return int(text, 2)
