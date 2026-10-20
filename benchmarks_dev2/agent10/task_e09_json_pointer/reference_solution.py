import copy


def _tokens(p):
    if not isinstance(p, str):
        raise TypeError("pointer must be a str")
    if p == "":
        return []
    if p[0] != "/":
        raise ValueError("pointer must start with /")
    out = []
    for t in p[1:].split("/"):
        j = 0
        while True:
            j = t.find("~", j)
            if j < 0:
                break
            if j + 1 >= len(t) or t[j + 1] not in "01":
                raise ValueError("bad escape")
            j += 2
        out.append(t.replace("~1", "/").replace("~0", "~"))
    return out


def _index(tok, n, allow_end=False, allow_dash=False):
    if tok == "-" and allow_dash:
        return n
    if not tok.isascii() or not tok.isdigit() or (len(tok) > 1 and tok[0] == "0"):
        raise ValueError("bad list index")
    i = int(tok)
    if i > (n if allow_end else n - 1):
        raise IndexError(tok)
    return i


def _step(cur, tok):
    if isinstance(cur, dict):
        if tok not in cur:
            raise KeyError(tok)
        return cur[tok]
    if isinstance(cur, list):
        return cur[_index(tok, len(cur))]
    raise KeyError(tok)


def pointer_get(doc, pointer):
    cur = doc
    for tok in _tokens(pointer):
        cur = _step(cur, tok)
    return cur


def pointer_set(doc, pointer, value):
    toks = _tokens(pointer)
    if not toks:
        return copy.deepcopy(value)
    new = copy.deepcopy(doc)
    cur = new
    for tok in toks[:-1]:
        cur = _step(cur, tok)
    last = toks[-1]
    if isinstance(cur, dict):
        cur[last] = copy.deepcopy(value)
    elif isinstance(cur, list):
        i = _index(last, len(cur), allow_end=True, allow_dash=True)
        if i == len(cur):
            cur.append(copy.deepcopy(value))
        else:
            cur[i] = copy.deepcopy(value)
    else:
        raise KeyError(last)
    return new
