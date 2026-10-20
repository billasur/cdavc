from urllib.parse import unquote


def parse_query(qs):
    if not isinstance(qs, str):
        raise TypeError("qs must be a str")
    if qs.startswith("?"):
        qs = qs[1:]
    out = {}
    for pair in qs.split("&"):
        if pair == "":
            continue
        k, _, v = pair.partition("=")
        k = unquote(k.replace("+", " "))
        v = unquote(v.replace("+", " "))
        as_list = False
        if k.endswith("[]"):
            k = k[:-2]
            as_list = True
        if k == "":
            continue
        if k in out:
            if not isinstance(out[k], list):
                out[k] = [out[k]]
            out[k].append(v)
        else:
            out[k] = [v] if as_list else v
    return out
