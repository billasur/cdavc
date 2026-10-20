def wrap_text(text, width):
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if isinstance(width, bool) or not isinstance(width, int):
        raise TypeError("width must be an int")
    if width < 1:
        raise ValueError("width must be >= 1")
    paragraphs, cur = [], []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                paragraphs.append(cur)
                cur = []
        else:
            cur.extend(line.split())
    if cur:
        paragraphs.append(cur)
    out = []
    for i, words in enumerate(paragraphs):
        if i:
            out.append("")
        line = ""
        for w in words:
            if len(w) > width:
                if line:
                    out.append(line)
                    line = ""
                while len(w) > width:
                    out.append(w[:width])
                    w = w[width:]
                line = w
            elif not line:
                line = w
            elif len(line) + 1 + len(w) <= width:
                line += " " + w
            else:
                out.append(line)
                line = w
        if line:
            out.append(line)
    return out
