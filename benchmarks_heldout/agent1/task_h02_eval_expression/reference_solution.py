"""Evaluate arithmetic expression strings with a recursive-descent parser."""

from fractions import Fraction


def _evaluate(expression: str) -> Fraction:
    pos = 0
    length = len(expression)

    def skip_space():
        nonlocal pos
        while pos < length and expression[pos].isspace():
            pos += 1

    def parse_expression() -> Fraction:
        nonlocal pos
        value = parse_term()
        while True:
            skip_space()
            if pos < length and expression[pos] in "+-":
                operator = expression[pos]
                pos += 1
                rhs = parse_term()
                value = value + rhs if operator == "+" else value - rhs
            else:
                return value

    def parse_term() -> Fraction:
        nonlocal pos
        value = parse_factor()
        while True:
            skip_space()
            if pos < length and expression[pos] in "*/":
                operator = expression[pos]
                pos += 1
                rhs = parse_factor()
                if operator == "*":
                    value = value * rhs
                else:
                    if rhs == 0:
                        raise ValueError("division by zero")
                    value = value / rhs
            else:
                return value

    def parse_factor() -> Fraction:
        nonlocal pos
        skip_space()
        if pos >= length:
            raise ValueError("unexpected end of expression")
        char = expression[pos]
        if char == "-":
            pos += 1
            return -parse_factor()
        if char == "+":
            pos += 1
            return parse_factor()
        if char == "(":
            pos += 1
            value = parse_expression()
            skip_space()
            if pos >= length or expression[pos] != ")":
                raise ValueError("missing closing parenthesis")
            pos += 1
            return value
        start = pos
        while pos < length and expression[pos].isdigit():
            pos += 1
        if start == pos:
            raise ValueError(f"unexpected character: {char!r}")
        return Fraction(int(expression[start:pos]))

    skip_space()
    if pos >= length:
        raise ValueError("empty expression")
    result = parse_expression()
    skip_space()
    if pos != length:
        raise ValueError(f"unexpected trailing input at position {pos}")
    return result


def eval_expression(expression: str):
    result = _evaluate(expression)
    if result.denominator == 1:
        return int(result)
    return float(result)
