def _match(s, i):
    depth = 0
    j = i
    n = len(s)
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return None


def _top_commas(s, i, j):
    depth = 0
    out = []
    k = i
    while k <= j:
        c = s[k]
        if c == "\\":
            k += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "," and depth == 1:
            out.append(k)
        k += 1
    return out


def _cat(results, opts):
    return [r + o for r in results for o in opts]


def _expand(s):
    results = [""]
    buf = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 < n:
                buf.append(s[i + 1])
                i += 2
            else:
                buf.append("\\")
                i += 1
            continue
        if c == "{":
            j = _match(s, i)
            if j is None:
                buf.append("{")
                i += 1
                continue
            commas = _top_commas(s, i, j)
            if buf:
                results = _cat(results, ["".join(buf)])
                buf = []
            if commas:
                bounds = [i] + commas + [j]
                opts = []
                for k in range(len(bounds) - 1):
                    opts.extend(_expand(s[bounds[k] + 1:bounds[k + 1]]))
                results = _cat(results, opts)
            else:
                results = _cat(results, ["{" + x + "}" for x in _expand(s[i + 1:j])])
            i = j + 1
            continue
        buf.append(c)
        i += 1
    if buf:
        results = _cat(results, ["".join(buf)])
    return results


def expand_braces(s):
    if not isinstance(s, str):
        raise TypeError("s must be a str")
    return _expand(s)
