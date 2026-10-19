def balanced_brackets(text: str) -> bool:
    matching = {")": "(", "]": "[", "}": "{"}
    openings = set(matching.values())
    stack = []
    for character in text:
        if character in openings:
            stack.append(character)
        elif character in matching:
            if not stack or stack.pop() != matching[character]:
                return False
    return not stack
