import re


def roman_to_int(numeral: str) -> int:
    if not re.fullmatch(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", numeral):
        raise ValueError("invalid Roman numeral")
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for index, character in enumerate(numeral):
        value = values[character]
        total += -value if index + 1 < len(numeral) and value < values[numeral[index + 1]] else value
    return total
