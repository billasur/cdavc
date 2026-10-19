def count_vowels(text: str) -> int:
    return sum(character.lower() in "aeiou" for character in text)
