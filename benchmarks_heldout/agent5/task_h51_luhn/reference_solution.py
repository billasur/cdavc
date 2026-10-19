def luhn_valid(text: str) -> bool:
    digits = []
    for ch in text:
        if ch in " -":
            continue
        if ch not in "0123456789":
            return False
        digits.append(int(ch))
    if len(digits) < 2:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
