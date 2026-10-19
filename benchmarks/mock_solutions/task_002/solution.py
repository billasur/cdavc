def is_palindrome(text: str) -> bool:
    normalized = "".join(character.lower() for character in text if character.isalnum())
    return normalized == normalized[::-1]
