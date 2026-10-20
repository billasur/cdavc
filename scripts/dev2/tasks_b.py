TASKS = []

TASKS.append(dict(
id="task_e08_case_convert", title="camelCase and snake_case conversion with acronyms", symbols=["camel_to_snake", "snake_to_camel"],
desc="Implement camel_to_snake(name) and snake_to_camel(name, upper_first=False); both require a str (TypeError). camel_to_snake lowercases the name and inserts '_' at word boundaries: between a lowercase letter or digit and a following uppercase letter ('fooBar' gives 'foo_bar', 'v2Beta' gives 'v2_beta', 'base64Encode' gives 'base64_encode'), and between an acronym and the capitalised word that follows it ('HTTPServer' gives 'http_server', 'parseXMLFile' gives 'parse_xml_file'). Digits stay attached to the letters before them ('ipV4' gives 'ip_v4'). Underscores already in the input are kept and an '_' is never inserted next to an existing '_' ('foo_Bar' gives 'foo_bar'). snake_to_camel splits on '_' and ignores empty parts (so leading, trailing and doubled underscores vanish); every part is lowercased first; the first part stays lowercase (or is capitalised when upper_first is true) and each later part gets an uppercase first letter ('http_server' gives 'httpServer', 'HTTP_SERVER' gives 'httpServer', 'a_1_b' gives 'a1B'). Empty string returns ''.",
invariants=["Acronym handling: 'HTTPServer' -> 'http_server', 'getHTTPResponseCode' -> 'get_http_response_code', 'ABC' -> 'abc'.",
 "Digits: 'base64Encode' -> 'base64_encode', 'v2Beta' -> 'v2_beta', 'HTTP2Server' -> 'http2_server'.",
 "No doubled underscores: 'foo_Bar' -> 'foo_bar'; existing underscores are kept ('already_snake' unchanged).",
 "snake_to_camel lowercases every part before capitalising, drops empty parts, and honours upper_first.",
 "Non-str input raises TypeError; '' returns ''."],
stub='''"""Case conversion."""


def camel_to_snake(name):
    raise NotImplementedError


def snake_to_camel(name, upper_first=False):
    raise NotImplementedError
''',
ref='''
def camel_to_snake(name):
    if not isinstance(name, str):
        raise TypeError("name must be a str")
    out = []
    n = len(name)
    for i, c in enumerate(name):
        if c.isupper() and i > 0:
            p = name[i - 1]
            nxt = name[i + 1] if i + 1 < n else ""
            if p != "_" and (p.islower() or p.isdigit() or (p.isupper() and nxt.islower())):
                out.append("_")
        out.append(c.lower())
    return "".join(out)


def snake_to_camel(name, upper_first=False):
    if not isinstance(name, str):
        raise TypeError("name must be a str")
    out = []
    for i, part in enumerate(p for p in name.split("_") if p):
        part = part.lower()
        out.append(part if (i == 0 and not upper_first) else part[:1].upper() + part[1:])
    return "".join(out)
''',
wrong='''
def camel_to_snake(name):
    return name.lower()


def snake_to_camel(name, upper_first=False):
    return name
''',
pub='''
_eq(m.camel_to_snake("fooBar"), "foo_bar")
_eq(m.snake_to_camel("http_server"), "httpServer")
''',
hid='''
c2s, s2c = m.camel_to_snake, m.snake_to_camel
_eq(c2s("fooBar"), "foo_bar")
_eq(c2s("HTTPServer"), "http_server")
_eq(c2s("parseXMLFile"), "parse_xml_file")
_eq(c2s("getHTTPResponseCode"), "get_http_response_code")
_eq(c2s("base64Encode"), "base64_encode")
_eq(c2s("v2Beta"), "v2_beta")
_eq(c2s("ipV4"), "ip_v4")
_eq(c2s("HTTP2Server"), "http2_server")
_eq(c2s("foo_Bar"), "foo_bar")
_eq(c2s("already_snake"), "already_snake")
_eq(c2s("ABC"), "abc")
_eq(c2s("A"), "a")
_eq(c2s("aB"), "a_b")
_eq(c2s(""), "")
_eq(s2c("http_server"), "httpServer")
_eq(s2c("http_server", upper_first=True), "HttpServer")
_eq(s2c("HTTP_SERVER"), "httpServer")
_eq(s2c("a_1_b"), "a1B")
_eq(s2c("__x__y_"), "xY")
_eq(s2c("single"), "single")
_eq(s2c("single", True), "Single")
_eq(s2c(""), "")
_raises(TypeError, c2s, None)
_raises(TypeError, s2c, 5)
''',
reg='''
_eq(m.camel_to_snake(""), "")
'''))

TASKS.append(dict(
id="task_e09_json_pointer", title="JSON Pointer get and set", symbols=["pointer_get", "pointer_set"],
desc="Implement pointer_get(doc, pointer) and pointer_set(doc, pointer, value) with RFC 6901 style pointers. pointer must be a str (TypeError). '' refers to the whole document. A non-empty pointer must start with '/' (else ValueError). The pointer is split on '/'; in each token '~1' becomes '/' and '~0' becomes '~' (decode ~1 first, then ~0, so '~01' is the literal '~1'); a '~' not followed by 0 or 1 raises ValueError. For a dict the token is the key (missing key raises KeyError). For a list the token must be '0' or digits without leading zeros and without sign (otherwise ValueError); an index past the end raises IndexError. Traversing into a non-container (str, int, None) raises KeyError. pointer_get returns the addressed value; '-' is invalid there (ValueError). pointer_set returns a NEW deep-copied document and never mutates doc or keeps references to value: for a dict it sets or adds the key; for a list an existing index is replaced, '-' appends, and an index equal to len(list) also appends, a larger index raises IndexError. The parent path must already exist (missing intermediate key raises KeyError). pointer_set with '' returns a copy of value.",
invariants=["Escapes: '/a~1b' addresses key 'a/b'; '/m~0n' addresses 'm~n'; '/~01' addresses '~1'.",
 "'' is the whole document; '/' addresses the key '' (empty string).",
 "List tokens: '01', '+1', '-1', 'x' and (for get) '-' raise ValueError; '5' on a 2-item list raises IndexError.",
 "pointer_set does not mutate its input and appends with '-' or index == len; index > len raises IndexError.",
 "Missing dict key or missing intermediate raises KeyError; traversing into a scalar raises KeyError; a non-str pointer raises TypeError."],
stub='''"""JSON Pointer."""


def pointer_get(doc, pointer):
    raise NotImplementedError


def pointer_set(doc, pointer, value):
    raise NotImplementedError
''',
ref='''
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
''',
wrong='''
def pointer_get(doc, pointer):
    return doc


def pointer_set(doc, pointer, value):
    return doc
''',
pub='''
_eq(m.pointer_get({"a": {"b": [10, 20]}}, "/a/b/1"), 20)
_eq(m.pointer_set({"a": 1}, "/b", 2), {"a": 1, "b": 2})
''',
hid='''
g, s = m.pointer_get, m.pointer_set
doc = {"a": {"b": [10, 20]}, "": 5, "a/b": 1, "m~n": 2, "~1": 3, "n": None}
_eq(g(doc, "/a/b/1"), 20)
_eq(g(doc, ""), doc)
_eq(g(doc, "/"), 5)
_eq(g(doc, "/a~1b"), 1)
_eq(g(doc, "/m~0n"), 2)
_eq(g(doc, "/~01"), 3)
_eq(g(doc, "/n"), None)
_eq(g([[1]], "/0/0"), 1)
for bad in ("a", "/~2", "/~", "x"):
    _raises(ValueError, g, doc, bad)
for bad in ("/a/b/01", "/a/b/+1", "/a/b/-1", "/a/b/x", "/a/b/-"):
    _raises(ValueError, g, doc, bad)
_raises(IndexError, g, doc, "/a/b/5")
_raises(KeyError, g, doc, "/zzz")
_raises(KeyError, g, doc, "/a/b/0/x")
_raises(KeyError, g, doc, "/n/x")
_raises(TypeError, g, doc, 5)
base = {"a": {"b": [10, 20]}}
r = s(base, "/a/b/-", 30)
_eq(r, {"a": {"b": [10, 20, 30]}})
_eq(base, {"a": {"b": [10, 20]}})
_eq(s(base, "/a/b/2", 30), {"a": {"b": [10, 20, 30]}})
_eq(s(base, "/a/b/0", 99), {"a": {"b": [99, 20]}})
_eq(s(base, "/a/c", 1), {"a": {"b": [10, 20], "c": 1}})
_eq(s(base, "", {"x": 1}), {"x": 1})
_raises(IndexError, s, base, "/a/b/3", 1)
_raises(KeyError, s, base, "/q/r", 1)
_raises(ValueError, s, base, "/a/b/01", 1)
_raises(TypeError, s, base, None, 1)
val = {"k": [1]}
out = s({}, "/v", val)
val["k"].append(2)
_eq(out, {"v": {"k": [1]}})
_eq(base, {"a": {"b": [10, 20]}})
''',
reg='''
_eq(m.pointer_get({"a": 1}, ""), {"a": 1})
'''))

TASKS.append(dict(
id="task_e10_check_brackets", title="Bracket checker that skips string literals", symbols=["check_brackets"],
desc="Implement check_brackets(s). It returns -1 when all brackets are balanced, otherwise the 0-based index of the first problem. Pairs are (), [], {}. Brackets inside string literals are ignored. A literal starts at ' or \" and ends at the next identical quote that is not escaped; inside a literal a backslash escapes the next character. Outside literals a backslash is an ordinary character. Scan left to right: a closing bracket that does not match the most recently opened bracket (or arrives with nothing open) is the problem and its own index is returned immediately. At the end of input: if a string literal is still open, return the index of its opening quote (this wins over unclosed brackets); otherwise if brackets are still open, return the index of the most recently opened one; otherwise -1. s must be a str (TypeError).",
invariants=["'(]' returns 1, ')' returns 0, '([)]' returns 2: a mismatched closer reports its own index.",
 "'((' returns 1 and '(()' returns 0: unclosed openers report the innermost unclosed opener (top of stack at the end).",
 "Brackets inside quotes are ignored: 'f(\"a)\")' is balanced; an escaped quote r'(\"a\\\\\"\")' does not end the literal.",
 "An unterminated literal returns the index of its opening quote even if brackets are also open ('( \"abc' returns 2).",
 "Outside a literal a backslash is ordinary: r'\\\\(' returns 1."],
stub='''"""Bracket checker."""


def check_brackets(s):
    raise NotImplementedError
''',
ref='''
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
            if c == "\\\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\\"":
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
''',
wrong='''
def check_brackets(s):
    return -1
''',
pub='''
_eq(m.check_brackets("(a)"), -1)
_eq(m.check_brackets("(]"), 1)
''',
hid=r'''
f = m.check_brackets
_eq(f("(a[b]{c})"), -1)
_eq(f(""), -1)
_eq(f("(]"), 1)
_eq(f(")"), 0)
_eq(f("(()"), 0)
_eq(f("(("), 1)
_eq(f("([)]"), 2)
_eq(f("'(' )"), 4)
_eq(f('f("a)")'), -1)
_eq(f(r'("a\"")'), -1)
_eq(f('x "abc'), 2)
_eq(f('( "abc'), 2)
_eq(f("\\("), 1)
_eq(f("'\"' ("), 4)
_eq(f("'abc\\'"), 0)
_eq(f("{[()]}"), -1)
_eq(f("{[(])}"), 3)
_eq(f("a)b("), 1)
_raises(TypeError, f, None)
''',
reg='''
_eq(m.check_brackets(""), -1)
'''))

TASKS.append(dict(
id="task_e11_min_coins", title="Fewest coins with deterministic tie-break", symbols=["min_coins"],
desc="Implement min_coins(coins, amount). coins is a list or tuple of positive ints (denominations; duplicates and any order are allowed), amount is an int >= 0. Return a list of coin values sorted descending that sums to amount using the fewest coins. When several multisets have the same number of coins, return the one that is lexicographically largest as a descending list (so with coins [1, 3, 4, 5] and amount 8 the answer is [5, 3], not [4, 4]). amount 0 returns []. If amount cannot be formed return None (empty coins with amount > 0 is None). Errors: coins not a list/tuple, or any coin not an int (bool rejected), or amount not an int (bool rejected) raise TypeError; a coin <= 0 or a negative amount raises ValueError. Coins are not required to be a canonical system (greedy is wrong for [1, 3, 4] and 6).",
invariants=["Fewest coins wins even when greedy would use more: min_coins([1, 3, 4], 6) == [3, 3].",
 "Ties go to the lexicographically largest descending list: min_coins([1, 3, 4, 5], 8) == [5, 3].",
 "Duplicates in coins are harmless; the result is sorted descending; amount 0 gives [].",
 "Impossible amounts give None (min_coins([2], 3) is None, min_coins([], 5) is None), not an exception.",
 "Type problems raise TypeError, non-positive coins or negative amounts raise ValueError."],
stub='''"""Fewest coins."""


def min_coins(coins, amount):
    raise NotImplementedError
''',
ref='''
def min_coins(coins, amount):
    if not isinstance(coins, (list, tuple)):
        raise TypeError("coins must be a list or tuple")
    for c in coins:
        if isinstance(c, bool) or not isinstance(c, int):
            raise TypeError("coins must be ints")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("amount must be an int")
    if any(c <= 0 for c in coins) or amount < 0:
        raise ValueError("bad value")
    cs = sorted(set(coins))
    best = [None] * (amount + 1)
    best[0] = []
    for a in range(1, amount + 1):
        cand = None
        for c in cs:
            if c <= a and best[a - c] is not None:
                t = sorted(best[a - c] + [c], reverse=True)
                key = (len(t), [-x for x in t])
                if cand is None or key < cand[0]:
                    cand = (key, t)
        best[a] = cand[1] if cand else None
    return best[amount]
''',
wrong='''
def min_coins(coins, amount):
    return None
''',
pub='''
_eq(m.min_coins([1, 3, 4], 6), [3, 3])
_eq(m.min_coins([2], 3), None)
''',
hid='''
f = m.min_coins
_eq(f([1, 3, 4], 6), [3, 3])
_eq(f([1, 3, 4, 5], 8), [5, 3])
_eq(f([2], 3), None)
_eq(f([], 0), [])
_eq(f([], 5), None)
_eq(f([5, 1, 5], 10), [5, 5])
_eq(f([1], 0), [])
_eq(f([25, 10, 5, 1], 63), [25, 25, 10, 1, 1, 1])
_eq(f([9, 6, 5, 1], 11), [6, 5])
_eq(f([3, 7], 11), None)
_eq(f([7, 3], 10), [7, 3])
_eq(f((2, 5), 9), [5, 2, 2])
_raises(ValueError, f, [1, 0], 3)
_raises(ValueError, f, [1, -2], 3)
_raises(ValueError, f, [1], -1)
_raises(TypeError, f, [1, "2"], 3)
_raises(TypeError, f, [1, True], 3)
_raises(TypeError, f, [1.0], 3)
_raises(TypeError, f, "12", 3)
_raises(TypeError, f, [1], 2.0)
_raises(TypeError, f, [1], True)
''',
reg='''
_eq(m.min_coins([1], 3), [1, 1, 1])
'''))

TASKS.append(dict(
id="task_e12_merge_sorted_lazy", title="Lazy stable merge of sorted iterables", symbols=["merge_sorted"],
desc="Implement merge_sorted(*iterables, key=None), a generator function that lazily merges already-sorted iterables into one sorted stream. The merge is stable: items that compare equal are yielded in iterable order (earlier iterable first) and, within one iterable, in their original order. When key is given, items are compared by key(item) and key is called exactly once per item. It must be lazy: nothing is read from any input before the first next(); it holds at most one pending item per input; after k items have been taken from the generator it has read at most (number of inputs) + (k - 1) items in total (an input is advanced only after its pending item has been yielded and the consumer asks for more). Inputs may be any iterables, including one-shot generators. With no iterables it yields nothing. Sortedness is not checked.",
invariants=["Basic merge: merge_sorted([1, 4, 7], [2, 5], [3, 6]) yields 1..7 in order.",
 "Stability with key: ties come out earlier-iterable first, items are never compared when keys are equal.",
 "key is called exactly once per item; no input is touched before the first next().",
 "Total items read after k items were taken is at most len(iterables) + k - 1 (do not read ahead).",
 "Works with one-shot generators and empty iterables; no iterables gives an empty stream."],
stub='''"""Lazy merge."""


def merge_sorted(*iterables, key=None):
    raise NotImplementedError
''',
ref='''
import heapq

_NONE = object()


def merge_sorted(*iterables, key=None):
    its = [iter(x) for x in iterables]
    heap = []
    for i, it in enumerate(its):
        for item in it:
            heap.append((item if key is None else key(item), i, item))
            break
    heapq.heapify(heap)
    while heap:
        _k, i, item = heap[0]
        yield item
        nxt = _NONE
        for x in its[i]:
            nxt = x
            break
        if nxt is _NONE:
            heapq.heappop(heap)
        else:
            heapq.heapreplace(heap, (nxt if key is None else key(nxt), i, nxt))
''',
wrong='''
def merge_sorted(*iterables, key=None):
    return iter([])
''',
pub='''
_eq(list(m.merge_sorted([1, 4, 7], [2, 5], [3, 6])), [1, 2, 3, 4, 5, 6, 7])
_eq(list(m.merge_sorted([(1, "a1"), (2, "a2")], [(1, "b1")], key=lambda t: t[0])), [(1, "a1"), (1, "b1"), (2, "a2")])
''',
hid='''
f = m.merge_sorted
_eq(list(f([1, 4, 7], [2, 5], [3, 6])), [1, 2, 3, 4, 5, 6, 7])
_eq(list(f()), [])
_eq(list(f([], [1], [])), [1])
_eq(list(f([1, 1], [1])), [1, 1, 1])
a = [(1, "a1"), (1, "a2"), (3, "a3")]
b = [(1, "b1"), (2, "b2")]
c = [(1, "c1")]
_eq(list(f(a, b, c, key=lambda t: t[0])), [(1, "a1"), (1, "a2"), (1, "b1"), (1, "c1"), (2, "b2"), (3, "a3")])
class Item:
    def __init__(self, k, tag):
        self.k, self.tag = k, tag
_eq([x.tag for x in f([Item(1, "a"), Item(2, "b")], [Item(1, "c")], key=lambda x: x.k)], ["a", "c", "b"])
calls = []
def key(x):
    calls.append(x)
    return x
out = list(f([1, 3, 5], [2, 4], key=key))
_eq(out, [1, 2, 3, 4, 5])
_eq(sorted(calls), [1, 2, 3, 4, 5])
pulled = [0]
def gen(items):
    for x in items:
        pulled[0] += 1
        yield x
g = f(gen([1, 4, 9]), gen([2, 3, 10]), gen([5]))
_eq(pulled[0], 0)
k = 0
expected = [1, 2, 3, 4, 5, 9, 10]
for want in expected:
    got = next(g)
    k += 1
    _eq(got, want)
    assert pulled[0] <= 3 + k - 1, f"read ahead: {pulled[0]} items read after {k} taken"
_eq(list(g), [])
''',
reg='''
_eq(list(m.merge_sorted()), [])
'''))

TASKS.append(dict(
id="task_e13_parse_query", title="URL query string parser", symbols=["parse_query"],
desc="Implement parse_query(qs) returning a dict from str keys to a str or a list of str. One leading '?' is stripped (only one: '??a=1' gives key '?a'). Pairs are separated by '&'; empty pairs ('a=1&&b=2', a trailing '&') are skipped. Each pair is split at the FIRST '=' ('a=b=c' gives {'a': 'b=c'}); a pair without '=' ('flag') has value ''. In both key and value, '+' becomes a space first and then percent-decoding is applied (so '%2B' stays a literal '+'); percent sequences are UTF-8; an invalid percent sequence ('%zz', a trailing '%') is kept literally; invalid UTF-8 bytes become U+FFFD. A pair whose decoded key is empty is skipped. A key name ending with '[]' has the '[]' removed and its value goes into a list. A key that appears several times (with or without '[]', in any mix) maps to a list of all its values in order; a key seen once without '[]' maps to a plain str. Dict order follows first appearance of each key. qs must be a str (TypeError).",
invariants=["Repeats collect: 'a=1&a=2&a=3' -> {'a': ['1', '2', '3']}; 'x[]=1' -> {'x': ['1']}; 'x=1&x[]=2' -> {'x': ['1', '2']}.",
 "'+' is a space but '%2B' is a plus: 'q=a+b' -> 'a b', 'q=a%2Bb' -> 'a+b'.",
 "Invalid escapes stay literal ('%zz', '100%'); '%E4' alone becomes U+FFFD; '%E2%82%AC' decodes to the euro sign.",
 "Splits at the first '=' only; no '=' means an empty value; empty pairs and empty keys are dropped.",
 "Only one leading '?' is removed; the result keeps first-appearance key order."],
stub='''"""Query string parser."""


def parse_query(qs):
    raise NotImplementedError
''',
ref='''
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
''',
wrong='''
def parse_query(qs):
    return {}
''',
pub='''
_eq(m.parse_query("a=1&b=2"), {"a": "1", "b": "2"})
_eq(m.parse_query("x[]=1&x[]=2"), {"x": ["1", "2"]})
''',
hid='''
f = m.parse_query
_eq(f("a=1&b=2"), {"a": "1", "b": "2"})
_eq(f("?a=1"), {"a": "1"})
_eq(f("??a=1"), {"?a": "1"})
_eq(f("a=1&&b=2&"), {"a": "1", "b": "2"})
_eq(f("flag"), {"flag": ""})
_eq(f("a=b=c"), {"a": "b=c"})
_eq(f("a=1&a=2&a=3"), {"a": ["1", "2", "3"]})
_eq(f("x[]=1"), {"x": ["1"]})
_eq(f("x[]=1&x[]=2"), {"x": ["1", "2"]})
_eq(f("x=1&x[]=2"), {"x": ["1", "2"]})
_eq(f("x[]=1&x=2"), {"x": ["1", "2"]})
_eq(f("q=a+b"), {"q": "a b"})
_eq(f("q=a%2Bb"), {"q": "a+b"})
_eq(f("q=%41%42"), {"q": "AB"})
_eq(f("q=%zz"), {"q": "%zz"})
_eq(f("q=100%"), {"q": "100%"})
_eq(f("q=%E4"), {"q": "\\ufffd"})
_eq(f("%E2%82%AC=eur"), {"\\u20ac": "eur"})
_eq(f("=v&k=1"), {"k": "1"})
_eq(f("[]=1&k=2"), {"k": "2"})
_eq(f("a="), {"a": ""})
_eq(f(""), {})
_eq(list(f("z=1&a=2&m=3")), ["z", "a", "m"])
_eq(f("a+b=c+d"), {"a b": "c d"})
_raises(TypeError, f, None)
''',
reg='''
_eq(m.parse_query(""), {})
'''))
