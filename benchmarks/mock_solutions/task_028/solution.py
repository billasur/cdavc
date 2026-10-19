import math


def evaluate_rpn(tokens: list[str]) -> int:
    stack = []
    operators = {"+", "-", "*", "/"}
    for token in tokens:
        if token not in operators:
            try:
                stack.append(int(token))
            except ValueError as exc:
                raise ValueError("invalid token") from exc
            continue
        if len(stack) < 2:
            raise ValueError("malformed expression")
        right = stack.pop()
        left = stack.pop()
        if token == "+":
            stack.append(left + right)
        elif token == "-":
            stack.append(left - right)
        elif token == "*":
            stack.append(left * right)
        else:
            if right == 0:
                raise ValueError("division by zero")
            stack.append(math.trunc(left / right))
    if len(stack) != 1:
        raise ValueError("malformed expression")
    return stack[0]
