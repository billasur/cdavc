def check_brackets(s):
    if not isinstance(s, str):
        raise TypeError("s must be a str")
    closers = {")": "(", "]": "[", "}": "{"}
    stack = []
    quote = None
    qi = -1
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if quote is not None:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"":
            quote, qi = c, i
        elif c in "([{":
            stack.append((c, i))
        elif c in closers:
            if not stack or stack[-1][0] != closers[c]:
                return i
            stack.pop()
        i += 1
    if quote is not None:
        return qi
    if stack:
        return stack[-1][1]
    return -1
