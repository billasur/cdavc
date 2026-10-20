TASKS = []

TASKS.append(dict(
id="task_e01_roman_strict", title="Strict Roman numerals", symbols=["to_roman", "from_roman"],
desc="Implement to_roman(n) and from_roman(s). to_roman: n must be an int (bool is rejected) else TypeError; 1..3999 inclusive else ValueError; returns the canonical uppercase subtractive form. from_roman: s must be a str else TypeError; it accepts only the canonical uppercase form of a number in 1..3999; anything else (empty, lowercase, surrounding spaces, non-canonical such as 'IIII', 'VX', 'IC', 'IIX', 'MMMM') raises ValueError.",
invariants=["to_roman(1994) is 'MCMXCIV' and uses subtractive pairs (IV, IX, XL, XC, CD, CM) only.",
 "from_roman accepts exactly the strings that to_roman can produce, so from_roman(to_roman(n)) == n for 1..3999.",
 "Non-canonical numerals ('IIII', 'VX', 'IC', 'IIX', 'VV') and lowercase or padded input raise ValueError, not a number.",
 "bool and float arguments to to_roman raise TypeError; out-of-range ints raise ValueError."],
stub='''"""Strict Roman numerals."""


def to_roman(n):
    raise NotImplementedError


def from_roman(s):
    raise NotImplementedError
''',
ref='''
_V = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
      (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if not 1 <= n <= 3999:
        raise ValueError("out of range")
    out = []
    for v, s in _V:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("s must be a str")
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    if not s or any(c not in vals for c in s):
        raise ValueError("bad numeral")
    total = 0
    for i, c in enumerate(s):
        v = vals[c]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    if not 1 <= total <= 3999 or to_roman(total) != s:
        raise ValueError("non-canonical")
    return total
''',
wrong='''
def to_roman(n):
    return str(n)


def from_roman(s):
    return len(s)
''',
pub='''
_eq(m.to_roman(4), "IV")
_eq(m.from_roman("XIV"), 14)
''',
hid='''
_eq(m.to_roman(1994), "MCMXCIV")
_eq(m.to_roman(3999), "MMMCMXCIX")
_eq(m.to_roman(444), "CDXLIV")
for n in range(1, 4000):
    _eq(m.from_roman(m.to_roman(n)), n)
for bad in (0, 4000, -5):
    _raises(ValueError, m.to_roman, bad)
for bad in (True, 3.0, "5", None):
    _raises(TypeError, m.to_roman, bad)
for bad in ("IIII", "VX", "IC", "MMMM", "", "iv", " IV", "IV ", "IIX", "XIIII", "VV", "IL", "XM", "ABC"):
    _raises(ValueError, m.from_roman, bad)
_raises(TypeError, m.from_roman, 5)
_raises(TypeError, m.from_roman, None)
''',
reg='''
_eq(m.to_roman(3), "III")
'''))

TASKS.append(dict(
id="task_e02_cron_field", title="Cron field expansion", symbols=["expand_field"],
desc="Implement expand_field(spec, lo, hi). Return the sorted list of unique ints matched by a cron-style field. spec is a str of comma-separated items. An item is '*' (every value lo..hi), 'N' (one value), or 'A-B' (inclusive range), each optionally followed by '/S' (step). '*/S' gives lo, lo+S, ... up to hi; 'A-B/S' steps from A up to B; 'N/S' means N, N+S, ... up to hi. Every value must satisfy lo <= v <= hi, else ValueError. A step must be a positive integer (0, negative, empty or non-numeric steps raise ValueError). A > B raises ValueError. An empty spec or any empty item (',1', '1,,2', '1,') raises ValueError. Numbers are plain ASCII digits only ('+1', '1.5', ' 1', '-1' raise ValueError). A non-str spec raises TypeError.",
invariants=["'*/15' over 0..59 is [0, 15, 30, 45]; '5/20' over 0..59 is [5, 25, 45] (a bare N with a step runs to hi).",
 "'1-5/2' is [1, 3, 5]; steps never go past the range end B.",
 "The result is sorted and has no duplicates ('5,1,5-6' over 0..10 is [1, 5, 6]).",
 "Out-of-range values, zero or malformed steps, reversed ranges and empty items raise ValueError.",
 "Only the first '-' splits a range, so '1-2-3' is invalid."],
stub='''"""Cron field expansion."""


def expand_field(spec, lo, hi):
    raise NotImplementedError
''',
ref='''
def _num(t, lo, hi):
    if not t.isascii() or not t.isdigit():
        raise ValueError("bad number")
    v = int(t)
    if not lo <= v <= hi:
        raise ValueError("out of range")
    return v


def expand_field(spec, lo, hi):
    if not isinstance(spec, str):
        raise TypeError("spec must be a str")
    if spec == "":
        raise ValueError("empty spec")
    out = set()
    for item in spec.split(","):
        if item == "":
            raise ValueError("empty item")
        base, sep, step_s = item.partition("/")
        step = None
        if sep:
            if not step_s.isascii() or not step_s.isdigit() or int(step_s) < 1:
                raise ValueError("bad step")
            step = int(step_s)
        if base == "*":
            a, b = lo, hi
        elif "-" in base:
            x, _, y = base.partition("-")
            a, b = _num(x, lo, hi), _num(y, lo, hi)
            if a > b:
                raise ValueError("reversed range")
        else:
            a = _num(base, lo, hi)
            b = a if step is None else hi
        out.update(range(a, b + 1, step or 1))
    return sorted(out)
''',
wrong='''
def expand_field(spec, lo, hi):
    return []
''',
pub='''
_eq(m.expand_field("*/15", 0, 59), [0, 15, 30, 45])
_eq(m.expand_field("1-3", 0, 59), [1, 2, 3])
''',
hid='''
f = m.expand_field
_eq(f("*/15", 0, 59), [0, 15, 30, 45])
_eq(f("1-5/2", 0, 59), [1, 3, 5])
_eq(f("5/20", 0, 59), [5, 25, 45])
_eq(f("1,3,5", 0, 59), [1, 3, 5])
_eq(f("5,1,5-6", 0, 10), [1, 5, 6])
_eq(f("*", 1, 3), [1, 2, 3])
_eq(f("0-6/7", 0, 6), [0])
_eq(f("3", 0, 6), [3])
_eq(f("*/1", 1, 3), [1, 2, 3])
_eq(f("*/100", 0, 59), [0])
_eq(f("2-4,3-5", 0, 9), [2, 3, 4, 5])
for bad in ("60", "", ",1", "1,,2", "1,", "*/0", "*/-1", "*/x", "5-1", "a", "1-", "-1", "+1", "1.5", " 1", "1 ", "*/", "1-5/0", "1-2-3", "/5"):
    _raises(ValueError, f, bad, 0, 59)
_raises(ValueError, f, "0", 1, 12)
_raises(ValueError, f, "13", 1, 12)
_raises(TypeError, f, None, 0, 59)
_raises(TypeError, f, 5, 0, 59)
''',
reg='''
_eq(m.expand_field("7", 0, 59), [7])
'''))

TASKS.append(dict(
id="task_e03_wrap_text", title="Greedy word wrap with paragraphs", symbols=["wrap_text"],
desc="Implement wrap_text(text, width) returning a list of lines. width must be an int (bool rejected) else TypeError, and >= 1 else ValueError; text must be a str else TypeError. Paragraphs are separated by one or more blank lines (a line holding only whitespace is blank); each paragraph is wrapped on its own and consecutive paragraphs are separated by a single '' element in the output. Within a paragraph words are split on any whitespace, runs collapse to one space, and lines never start or end with a space. Wrapping is greedy: a word joins the current line when line + ' ' + word fits within width. A word longer than width always starts a new line and is hard-split into chunks of exactly width characters; its final chunk becomes the current line and later words may join it if they fit. Empty or all-whitespace text returns []; leading and trailing blank lines are ignored.",
invariants=["Greedy fill: 'aaa bbb ccc' at width 7 is ['aaa bbb', 'ccc']; a line may be exactly width long.",
 "Runs of whitespace collapse; tabs and multiple spaces become one space.",
 "Blank or whitespace-only lines separate paragraphs; several blank lines give one '' separator; leading and trailing blank lines produce nothing.",
 "A long word starts a new line, is split into width-sized chunks, and its short tail can take following words ('ab abcdefghij c' at width 4 is ['ab', 'abcd', 'efgh', 'ij c']).",
 "Bad width or text types raise TypeError; width < 1 raises ValueError."],
stub='''"""Greedy word wrap."""


def wrap_text(text, width):
    raise NotImplementedError
''',
ref='''
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
''',
wrong='''
def wrap_text(text, width):
    return [text]
''',
pub='''
_eq(m.wrap_text("aaa bbb ccc", 7), ["aaa bbb", "ccc"])
_eq(m.wrap_text("hello", 10), ["hello"])
''',
hid='''
f = m.wrap_text
_eq(f("aaa bbb ccc", 7), ["aaa bbb", "ccc"])
_eq(f("a  b\\tc", 3), ["a b", "c"])
_eq(f("one two\\n\\nthree", 7), ["one two", "", "three"])
_eq(f("a\\n  \\nb", 5), ["a", "", "b"])
_eq(f("a\\n\\n\\n\\nb", 5), ["a", "", "b"])
_eq(f("\\n\\nhello\\n\\n", 10), ["hello"])
_eq(f("abcdefghij", 4), ["abcd", "efgh", "ij"])
_eq(f("abcdefgh", 4), ["abcd", "efgh"])
_eq(f("ab abcdefghij c", 4), ["ab", "abcd", "efgh", "ij c"])
_eq(f("a b", 1), ["a", "b"])
_eq(f("ab cd", 5), ["ab cd"])
_eq(f("ab cd", 4), ["ab", "cd"])
_eq(f("line one\\nline two", 20), ["line one line two"])
_eq(f("", 5), [])
_eq(f("  \\n ", 5), [])
_raises(ValueError, f, "x", 0)
_raises(ValueError, f, "x", -1)
_raises(TypeError, f, "x", 2.0)
_raises(TypeError, f, "x", True)
_raises(TypeError, f, None, 5)
''',
reg='''
_eq(m.wrap_text("a", 1), ["a"])
'''))

TASKS.append(dict(
id="task_e04_osa_distance", title="Optimal string alignment distance with cutoff", symbols=["osa_distance"],
desc="Implement osa_distance(a, b, max_distance=None). It is the optimal string alignment distance: the minimum number of single-character insertions, deletions, substitutions and adjacent transpositions, where no substring is edited more than once (so osa_distance('ca', 'abc') is 3, not 2). a and b must be str else TypeError. If max_distance is not None it must be an int (bool rejected, else TypeError) and >= 0 (else ValueError); then return the distance when it is <= max_distance, otherwise return max_distance + 1.",
invariants=["An adjacent swap costs 1: osa_distance('ab', 'ba') == 1 and osa_distance('abc', 'acb') == 1.",
 "It is the restricted (OSA) variant, not true Damerau-Levenshtein: osa_distance('ca', 'abc') == 3.",
 "Plain Levenshtein cases hold: ('kitten', 'sitting') is 3, ('abc', '') is 3, equal strings are 0.",
 "With max_distance, results above the limit are reported as max_distance + 1 and results at or below it are exact.",
 "Non-str inputs and non-int or bool max_distance raise TypeError; negative max_distance raises ValueError."],
stub='''"""OSA distance."""


def osa_distance(a, b, max_distance=None):
    raise NotImplementedError
''',
ref='''
def osa_distance(a, b, max_distance=None):
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise TypeError("max_distance must be an int")
        if max_distance < 0:
            raise ValueError("max_distance must be >= 0")
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    r = d[n][m]
    if max_distance is not None and r > max_distance:
        return max_distance + 1
    return r
''',
wrong='''
def osa_distance(a, b, max_distance=None):
    return abs(len(a) - len(b))
''',
pub='''
_eq(m.osa_distance("kitten", "sitting"), 3)
_eq(m.osa_distance("ab", "ba"), 1)
''',
hid='''
f = m.osa_distance
_eq(f("", ""), 0)
_eq(f("abc", ""), 3)
_eq(f("", "abc"), 3)
_eq(f("kitten", "sitting"), 3)
_eq(f("ab", "ba"), 1)
_eq(f("ca", "abc"), 3)
_eq(f("abc", "acb"), 1)
_eq(f("a", "b"), 1)
_eq(f("flaw", "lawn"), 2)
_eq(f("same", "same"), 0)
_eq(f("ab", "a"), 1)
_eq(f("kitten", "sitting", 3), 3)
_eq(f("kitten", "sitting", 2), 3)
_eq(f("abc", "xyz", 0), 1)
_eq(f("a", "a", 0), 0)
_eq(f("abcd", "", 1), 2)
_raises(TypeError, f, 1, "a")
_raises(TypeError, f, "a", None)
_raises(ValueError, f, "a", "b", -1)
_raises(TypeError, f, "a", "b", 1.5)
_raises(TypeError, f, "a", "b", True)
''',
reg='''
_eq(m.osa_distance("a", "a"), 0)
'''))

TASKS.append(dict(
id="task_e05_brace_expand", title="Shell-style brace expansion", symbols=["expand_braces"],
desc="Implement expand_braces(s) returning a list of strings. 'a{b,c}d' gives ['abd', 'acd']. Groups nest ('{a,b{c,d}}' gives ['a', 'bc', 'bd']). Several groups form a cartesian product in which the leftmost group varies slowest ('{a,b}{1,2}' gives ['a1', 'a2', 'b1', 'b2']). Empty alternatives are allowed ('x{,y}' gives ['x', 'xy']). A group with no top-level comma ('{a}', '{}', '{{a,b}}') is NOT expanded and stays as literal braces, but braces nested inside it are still expanded ('{x{1,2}}' gives ['{x1}', '{x2}'], '{{a,b}}' gives ['{a}', '{b}']). A backslash escapes the next character: the escaped character is literal (it never opens, closes or splits a group) and the backslash is removed. An unmatched '{' and any stray '}' are literal. Duplicates are kept. s must be a str else TypeError; '' gives [''].",
invariants=["Order is left to right with the leftmost group varying slowest.",
 "A single-alternative group or empty group is literal: '{a}' stays '{a}' and '{}' stays '{}'.",
 "Escapes: r'\\\\{a,b\\\\}' is the literal '{a,b}', and r'{a\\\\,b,c}' is ['a,b', 'c'].",
 "Unmatched '{' ('{a,b') and stray '}' ('a}b') are literal.",
 "Nested groups expand recursively; commas only split at the top level of their own group."],
stub='''"""Brace expansion."""


def expand_braces(s):
    raise NotImplementedError
''',
ref='''
def _match(s, i):
    depth = 0
    j = i
    n = len(s)
    while j < n:
        c = s[j]
        if c == "\\\\":
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
        if c == "\\\\":
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
        if c == "\\\\":
            if i + 1 < n:
                buf.append(s[i + 1])
                i += 2
            else:
                buf.append("\\\\")
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
''',
wrong='''
def expand_braces(s):
    return [s]
''',
pub='''
_eq(m.expand_braces("a{b,c}d"), ["abd", "acd"])
_eq(m.expand_braces("{a,b}{1,2}"), ["a1", "a2", "b1", "b2"])
''',
hid=r'''
f = m.expand_braces
_eq(f("a{b,c}d"), ["abd", "acd"])
_eq(f("{a,b{c,d}}"), ["a", "bc", "bd"])
_eq(f("{a,b}{1,2}"), ["a1", "a2", "b1", "b2"])
_eq(f("x{,y}"), ["x", "xy"])
_eq(f("{a}"), ["{a}"])
_eq(f("{}"), ["{}"])
_eq(f("{x{1,2}}"), ["{x1}", "{x2}"])
_eq(f("{{a,b}}"), ["{a}", "{b}"])
_eq(f(r"\{a,b\}"), ["{a,b}"])
_eq(f(r"{a\,b,c}"), ["a,b", "c"])
_eq(f(r"\\{a,b}"), ["\\a", "\\b"])
_eq(f("{a,b"), ["{a,b"])
_eq(f("a}b"), ["a}b"])
_eq(f(""), [""])
_eq(f("plain"), ["plain"])
_eq(f("{a,a}"), ["a", "a"])
_eq(f("{a,b}c{d,e}"), ["acd", "ace", "bcd", "bce"])
_eq(f("{,}"), ["", ""])
_eq(f("{a,{b,c}}"), ["a", "b", "c"])
_raises(TypeError, f, None)
''',
reg='''
_eq(m.expand_braces("abc"), ["abc"])
'''))

TASKS.append(dict(
id="task_e06_interval_set", title="Half-open integer interval set", symbols=["IntervalSet"],
desc="Implement class IntervalSet holding a set of integers as half-open ranges [start, end). Methods: add(start, end), remove(start, end), contains(x), total(), intervals(). add and remove require ints (bool rejected, TypeError) with start <= end (else ValueError); start == end is a no-op. add merges overlapping AND touching ranges ([1,3) plus [3,5) becomes [1,5)). remove cuts ranges and may split one range in two. intervals() returns a new sorted list of (start, end) tuples that is normalised (no empty, overlapping or touching ranges); mutating the returned list must not change the set. contains(x) is True when start <= x < end for some range (x must be an int, bool rejected, else TypeError). total() is the count of integers covered. add and remove return None. Negative numbers are allowed.",
invariants=["Touching ranges merge: add(1,3) then add(3,5) gives [(1, 5)].",
 "A bridging add merges every range it touches: ranges [1,2),[4,5),[7,8) plus add(2,7) give [(1, 8)].",
 "remove can split: [1,10) minus [4,6) gives [(1, 4), (6, 10)]; removing a touching range changes nothing.",
 "Ranges are half-open: contains(end) is False, contains(start) is True.",
 "intervals() returns a copy; start > end raises ValueError; non-int or bool raises TypeError."],
stub='''"""Interval set."""


class IntervalSet:
    def add(self, start, end):
        raise NotImplementedError

    def remove(self, start, end):
        raise NotImplementedError

    def contains(self, x):
        raise NotImplementedError

    def total(self):
        raise NotImplementedError

    def intervals(self):
        raise NotImplementedError
''',
ref='''
class IntervalSet:
    def __init__(self):
        self._iv = []

    @staticmethod
    def _check(a, b):
        for v in (a, b):
            if isinstance(v, bool) or not isinstance(v, int):
                raise TypeError("ints required")
        if a > b:
            raise ValueError("start > end")

    def add(self, start, end):
        self._check(start, end)
        if start == end:
            return None
        out = []
        s, e = start, end
        for a, b in self._iv:
            if b < s or a > e:
                out.append((a, b))
            else:
                s, e = min(s, a), max(e, b)
        out.append((s, e))
        out.sort()
        self._iv = out
        return None

    def remove(self, start, end):
        self._check(start, end)
        if start == end:
            return None
        out = []
        for a, b in self._iv:
            if b <= start or a >= end:
                out.append((a, b))
                continue
            if a < start:
                out.append((a, start))
            if b > end:
                out.append((end, b))
        self._iv = out
        return None

    def contains(self, x):
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError("x must be an int")
        return any(a <= x < b for a, b in self._iv)

    def total(self):
        return sum(b - a for a, b in self._iv)

    def intervals(self):
        return list(self._iv)
''',
wrong='''
class IntervalSet:
    def add(self, start, end):
        return None

    def remove(self, start, end):
        return None

    def contains(self, x):
        return False

    def total(self):
        return 0

    def intervals(self):
        return []
''',
pub='''
s = m.IntervalSet()
s.add(1, 3)
s.add(5, 8)
_eq(s.intervals(), [(1, 3), (5, 8)])
_eq(s.total(), 5)
''',
hid='''
S = m.IntervalSet
s = S(); s.add(1, 3); s.add(3, 5)
_eq(s.intervals(), [(1, 5)])
s = S(); s.add(5, 7); s.add(1, 3)
_eq(s.intervals(), [(1, 3), (5, 7)])
s = S(); s.add(1, 10); s.remove(4, 6)
_eq(s.intervals(), [(1, 4), (6, 10)])
s.remove(10, 12); s.remove(0, 1)
_eq(s.intervals(), [(1, 4), (6, 10)])
s.remove(0, 100)
_eq(s.intervals(), [])
s = S(); s.add(1, 2); s.add(4, 5); s.add(7, 8); s.add(2, 7)
_eq(s.intervals(), [(1, 8)])
s = S(); s.add(1, 2); s.add(5, 6); s.add(3, 4)
_eq(s.intervals(), [(1, 2), (3, 4), (5, 6)])
s = S(); s.add(0, 0)
_eq(s.intervals(), [])
s = S(); s.add(1, 3)
_eq((s.contains(0), s.contains(1), s.contains(2), s.contains(3)), (False, True, True, False))
s = S(); s.add(-5, -2)
_eq((s.contains(-5), s.contains(-2), s.total()), (True, False, 3))
s = S(); s.add(1, 10); s.remove(1, 4)
_eq(s.intervals(), [(4, 10)])
s.remove(8, 10)
_eq(s.intervals(), [(4, 8)])
got = s.intervals(); got.append((99, 100))
_eq(s.intervals(), [(4, 8)])
_eq(s.add(1, 2), None)
_eq(s.remove(1, 2), None)
_raises(ValueError, s.add, 3, 1)
_raises(ValueError, s.remove, 3, 1)
_raises(TypeError, s.add, 1.0, 2)
_raises(TypeError, s.add, True, 2)
_raises(TypeError, s.contains, "1")
_raises(TypeError, s.contains, True)
s = S(); s.add(1, 5); s.add(2, 3)
_eq((s.intervals(), s.total()), ([(1, 5)], 4))
''',
reg='''
_eq(m.IntervalSet().total(), 0)
'''))

TASKS.append(dict(
id="task_e07_format_bytes", title="Human-readable byte sizes", symbols=["format_bytes"],
desc="Implement format_bytes(n, binary=False). Decimal mode uses base 1000 and units B, kB, MB, GB, TB, PB; binary mode uses base 1024 and units B, KiB, MiB, GiB, TiB, PiB. n must be an int (bool rejected, TypeError) and >= 0 (ValueError). Values below the base print as '<n> B' with no decimals. Otherwise pick the largest unit whose value is >= 1, round to ONE decimal using round-half-up on the exact value (integer arithmetic, no float error), and print '<value> <unit>' with exactly one decimal ('1.0 kB'). If rounding reaches the base (999950 bytes is 999.95 kB which rounds to 1000.0) promote to the next unit ('1.0 MB'). PB / PiB is the largest unit and may print values of 1000 or more.",
invariants=["999 is '999 B', 1000 is '1.0 kB', 1500 is '1.5 kB'; binary 1023 is '1023 B', 1024 is '1.0 KiB'.",
 "Round half up: 1050 bytes is '1.1 kB', 1049 is '1.0 kB'.",
 "Rollover: 999949 is '999.9 kB', 999950 is '1.0 MB'; binary 1048575 is '1.0 MiB'.",
 "Always exactly one decimal for non-B units; never more than PB/PiB ('10000.0 PB' for 10**19).",
 "Negative raises ValueError; float, str and bool raise TypeError."],
stub='''"""Human-readable byte sizes."""


def format_bytes(n, binary=False):
    raise NotImplementedError
''',
ref='''
def format_bytes(n, binary=False):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n < 0:
        raise ValueError("n must be >= 0")
    base = 1024 if binary else 1000
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"] if binary else ["B", "kB", "MB", "GB", "TB", "PB"]
    if n < base:
        return f"{n} B"
    k = 1
    while k < 5 and n >= base ** (k + 1):
        k += 1

    def tenths(k):
        d = base ** k
        return (n * 20 + d) // (2 * d)

    t = tenths(k)
    if t >= base * 10 and k < 5:
        k += 1
        t = tenths(k)
    return f"{t // 10}.{t % 10} {units[k]}"
''',
wrong='''
def format_bytes(n, binary=False):
    return f"{n} B"
''',
pub='''
_eq(m.format_bytes(1000), "1.0 kB")
_eq(m.format_bytes(1500), "1.5 kB")
''',
hid='''
f = m.format_bytes
_eq(f(0), "0 B")
_eq(f(999), "999 B")
_eq(f(1000), "1.0 kB")
_eq(f(1500), "1.5 kB")
_eq(f(1050), "1.1 kB")
_eq(f(1049), "1.0 kB")
_eq(f(999949), "999.9 kB")
_eq(f(999950), "1.0 MB")
_eq(f(5 * 10**6), "5.0 MB")
_eq(f(1023, binary=True), "1023 B")
_eq(f(1024, binary=True), "1.0 KiB")
_eq(f(1536, binary=True), "1.5 KiB")
_eq(f(1048575, binary=True), "1.0 MiB")
_eq(f(10**19), "10000.0 PB")
_raises(ValueError, f, -1)
_raises(TypeError, f, 1.5)
_raises(TypeError, f, True)
_raises(TypeError, f, "1")
''',
reg='''
_eq(m.format_bytes(0), "0 B")
'''))
