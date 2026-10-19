def title_case(text):
    return " ".join(word[:1].upper() + word[1:].lower() for word in text.split())
