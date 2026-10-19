"""Authoring data for the dev corpus (``benchmarks/dev``).

Forty small, single-function tasks in the style of the held-out corpus but
disjoint from it.  Each entry carries the reference implementation, the
public / hidden / regression arguments, and the property shape used to
generate differential cases.  Expected values are not written by hand: the
build script derives them from the reference and refuses to emit a corpus
unless every case agrees.

Keep this file data-only.  ``tools/build_dev_corpus.py`` renders it.
"""

from __future__ import annotations

from typing import Any


def ok(*args: Any) -> tuple[tuple[Any, ...], None]:
    return (args, None)


def bad(exc: str, *args: Any) -> tuple[tuple[Any, ...], str]:
    return (args, exc)


def T(
    tid: str,
    symbol: str,
    shape: str,
    description: str,
    ref: str,
    public: list[tuple[tuple[Any, ...], str | None]],
    hidden: list[tuple[tuple[Any, ...], str | None]],
    regression: list[tuple[tuple[Any, ...], str | None]],
    invariants: list[str] | None = None,
    pure: bool = True,
) -> dict[str, Any]:
    return {
        "tid": tid,
        "symbol": symbol,
        "shape": shape,
        "description": description,
        "ref": ref,
        "public": public,
        "hidden": hidden,
        "regression": regression,
        "invariants": invariants or [],
        "pure": pure,
    }


SPECS: list[dict[str, Any]] = [
    T(
        "dev_001",
        "second_largest",
        "intlist",
        "Implement second_largest(values). Return the second largest element after sorting, counting duplicates, or None when fewer than two elements are given.",
        '''def second_largest(values):
    if len(values) < 2:
        return None
    return sorted(values)[-2]
''',
        [ok([1, 2, 3]), ok([])],
        [ok([5, 5, 4]), ok([3])],
        [ok([9, 1])],
        ["Return None instead of raising when the list is short."],
    ),
    T(
        "dev_002",
        "caesar_shift",
        "text_int",
        "Implement caesar_shift(text, k). Shift ASCII letters by k positions, wrapping within a-z and A-Z and preserving case; leave every other character unchanged.",
        '''def caesar_shift(text, k):
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - ord("a") + k) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - ord("A") + k) % 26 + ord("A")))
        else:
            out.append(ch)
    return "".join(out)
''',
        [ok("abc", 1), ok("", 3)],
        [ok("xyz", 3), ok("Hello, World!", 0)],
        [ok("abc", 26)],
        ["Non-letters are copied unchanged."],
    ),
    T(
        "dev_003",
        "title_case",
        "text",
        "Implement title_case(text). Upper-case the first letter of every whitespace-separated word, lower-case the rest, and join words with a single space.",
        '''def title_case(text):
    return " ".join(word[:1].upper() + word[1:].lower() for word in text.split())
''',
        [ok("hello world"), ok("")],
        [ok("tHE qUICK"), ok("  a  b ")],
        [ok("MIXED case")],
    ),
    T(
        "dev_004",
        "collapse_spaces",
        "text",
        "Implement collapse_spaces(text). Replace every run of whitespace with one space and strip leading and trailing whitespace.",
        '''def collapse_spaces(text):
    return " ".join(text.split())
''',
        [ok("a  b"), ok("   ")],
        [ok(" a\\tb\\n c "), ok("")],
        [ok("one")],
    ),
    T(
        "dev_005",
        "count_substring",
        "text2",
        "Implement count_substring(text, needle). Count non-overlapping occurrences; an empty needle counts zero.",
        '''def count_substring(text, needle):
    if not needle:
        return 0
    return text.count(needle)
''',
        [ok("aaaa", "aa"), ok("abc", "")],
        [ok("banana", "an"), ok("abc", "z")],
        [ok("aaa", "a")],
    ),
    T(
        "dev_006",
        "truncate",
        "text_width",
        "Implement truncate(text, width). Return text unchanged when it fits; otherwise cut to width characters, ending with three dots when width is at least 4, and strip the trailing space before the dots.",
        '''def truncate(text, width):
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3].rstrip() + "..."
''',
        [ok("hello", 5), ok("hello", 2)],
        [ok("hello world", 8), ok("ab cd", 4)],
        [ok("hello", 10)],
    ),
    T(
        "dev_007",
        "snake_to_camel",
        "snake",
        "Implement snake_to_camel(text). Convert underscore-separated lower-case words to camelCase; ignore empty segments and return an empty string for an empty input.",
        '''def snake_to_camel(text):
    parts = [part for part in text.split("_") if part]
    if not parts:
        return ""
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
''',
        [ok("foo_bar"), ok("")],
        [ok("a_b_c"), ok("foo__bar")],
        [ok("single")],
    ),
    T(
        "dev_008",
        "is_anagram",
        "text2",
        "Implement is_anagram(a, b). Compare case-insensitively after dropping every non-alphanumeric character.",
        '''def is_anagram(a, b):
    def normalise(text):
        return sorted(ch.lower() for ch in text if ch.isalnum())

    return normalise(a) == normalise(b)
''',
        [ok("listen", "silent"), ok("abc", "abd")],
        [ok("Dormitory", "dirty room"), ok("", "")],
        [ok("a b", "ba")],
    ),
    T(
        "dev_009",
        "digit_sum",
        "int_signed",
        "Implement digit_sum(n). Return the sum of the decimal digits of the absolute value; zero sums to zero.",
        '''def digit_sum(n):
    return sum(int(ch) for ch in str(abs(n)))
''',
        [ok(123), ok(0)],
        [ok(-405), ok(9)],
        [ok(1000)],
    ),
    T(
        "dev_010",
        "is_armstrong",
        "int",
        "Implement is_armstrong(n). Return True when n equals the sum of its digits each raised to the number of digits; n is non-negative.",
        '''def is_armstrong(n):
    digits = [int(ch) for ch in str(n)]
    return sum(digit ** len(digits) for digit in digits) == n
''',
        [ok(153), ok(100)],
        [ok(0), ok(9474)],
        [ok(9)],
    ),
    T(
        "dev_011",
        "factorial",
        "smallint",
        "Implement factorial(n). Return n! for a non-negative integer and raise ValueError for a negative input.",
        '''def factorial(n):
    if n < 0:
        raise ValueError("factorial is undefined for negative numbers")
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result
''',
        [ok(0), ok(5)],
        [bad("ValueError", -1), ok(10)],
        [ok(1)],
    ),
    T(
        "dev_012",
        "binomial",
        "int2nonneg",
        "Implement binomial(n, k). Return the binomial coefficient, and 0 when k is outside 0..n.",
        '''def binomial(n, k):
    if k < 0 or k > n:
        return 0
    result = 1
    for step in range(k):
        result = result * (n - step) // (step + 1)
    return result
''',
        [ok(5, 2), ok(3, 5)],
        [ok(0, 0), ok(10, 10)],
        [ok(6, 3)],
    ),
    T(
        "dev_013",
        "is_perfect_square",
        "int_signed",
        "Implement is_perfect_square(n). Return True only for non-negative perfect squares.",
        '''import math


def is_perfect_square(n):
    if n < 0:
        return False
    root = math.isqrt(n)
    return root * root == n
''',
        [ok(16), ok(15)],
        [ok(0), ok(-4)],
        [ok(1)],
    ),
    T(
        "dev_014",
        "clamp",
        "clamp",
        "Implement clamp(value, low, high). Return value limited to the inclusive range; raise ValueError when low is greater than high.",
        '''def clamp(value, low, high):
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))
''',
        [ok(5, 0, 10), ok(-1, 0, 10)],
        [ok(11, 0, 10), bad("ValueError", 1, 5, 4)],
        [ok(0, 0, 0)],
    ),
    T(
        "dev_015",
        "sign",
        "int_signed",
        "Implement sign(n). Return -1 for negative numbers, 0 for zero and 1 for positive numbers.",
        '''def sign(n):
    if n < 0:
        return -1
    if n > 0:
        return 1
    return 0
''',
        [ok(-3), ok(0)],
        [ok(7), ok(-1)],
        [ok(100)],
    ),
    T(
        "dev_016",
        "mean",
        "poslist",
        "Implement mean(values). Return the arithmetic mean rounded to six decimal places; raise ValueError for an empty list.",
        '''def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return round(sum(values) / len(values), 6)
''',
        [ok([1, 2, 3]), bad("ValueError", [])],
        [ok([2, 2]), ok([1])],
        [ok([10, 20])],
    ),
    T(
        "dev_017",
        "median",
        "poslist",
        "Implement median(values). Return the middle value, or the mean of the two middle values, rounded to six decimals; raise ValueError for an empty list.",
        '''def median(values):
    if not values:
        raise ValueError("median of an empty list")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return round((ordered[middle - 1] + ordered[middle]) / 2, 6)
''',
        [ok([3, 1, 2]), bad("ValueError", [])],
        [ok([4, 1, 3, 2]), ok([5])],
        [ok([2, 8])],
    ),
    T(
        "dev_018",
        "variance_population",
        "poslist",
        "Implement variance_population(values). Return the population variance rounded to six decimals; raise ValueError for an empty list.",
        '''def variance_population(values):
    if not values:
        raise ValueError("variance of an empty list")
    average = sum(values) / len(values)
    return round(sum((value - average) ** 2 for value in values) / len(values), 6)
''',
        [ok([1, 1]), bad("ValueError", [])],
        [ok([1, 2, 3]), ok([5])],
        [ok([2, 4])],
    ),
    T(
        "dev_019",
        "normalize_vector",
        "numlist",
        "Implement normalize_vector(values). Divide each value by the Euclidean norm and round to six decimals; a zero vector keeps its zeros as floats.",
        '''def normalize_vector(values):
    norm = sum(value * value for value in values) ** 0.5
    if norm == 0:
        return [0.0 for _ in values]
    return [round(value / norm, 6) for value in values]
''',
        [ok([3, 4]), ok([])],
        [ok([1, 0]), ok([0])],
        [ok([6, 8])],
    ),
    T(
        "dev_020",
        "dot_product",
        "same_pair_lists",
        "Implement dot_product(a, b). Return the sum of products; raise ValueError when the lengths differ.",
        '''def dot_product(a, b):
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return sum(left * right for left, right in zip(a, b))
''',
        [ok([1, 2], [3, 4]), bad("ValueError", [1], [1, 2])],
        [ok([], []), ok([-1, 2], [3, -4])],
        [ok([2, 0], [0, 3])],
    ),
    T(
        "dev_021",
        "cumulative_sum",
        "intlist",
        "Implement cumulative_sum(values). Return the running totals, starting with the first element.",
        '''def cumulative_sum(values):
    totals = []
    running = 0
    for value in values:
        running += value
        totals.append(running)
    return totals
''',
        [ok([1, 2, 3]), ok([])],
        [ok([-1, 1]), ok([5])],
        [ok([2, 2])],
    ),
    T(
        "dev_022",
        "pairwise_differences",
        "intlist",
        "Implement pairwise_differences(values). Return next minus current for every adjacent pair; a list shorter than two gives an empty list.",
        '''def pairwise_differences(values):
    return [values[index + 1] - values[index] for index in range(len(values) - 1)]
''',
        [ok([1, 3, 6]), ok([4])],
        [ok([]), ok([2, 2])],
        [ok([0, -1])],
    ),
    T(
        "dev_023",
        "interleave",
        "pair_lists",
        "Implement interleave(a, b). Alternate elements starting with a, appending any leftovers of the longer list.",
        '''def interleave(a, b):
    result = []
    for index in range(max(len(a), len(b))):
        if index < len(a):
            result.append(a[index])
        if index < len(b):
            result.append(b[index])
    return result
''',
        [ok([1, 2], [3, 4]), ok([], [1, 2])],
        [ok([1], []), ok([], [])],
        [ok([9], [8])],
    ),
    T(
        "dev_024",
        "take_while_positive",
        "intlist",
        "Implement take_while_positive(values). Return the longest prefix whose elements are greater than zero.",
        '''def take_while_positive(values):
    result = []
    for value in values:
        if value <= 0:
            break
        result.append(value)
    return result
''',
        [ok([1, 2, -1, 3]), ok([-1, 2])],
        [ok([]), ok([5])],
        [ok([1, 0])],
    ),
    T(
        "dev_025",
        "drop_while_negative",
        "intlist",
        "Implement drop_while_negative(values). Remove the longest prefix whose elements are below zero and return the rest.",
        '''def drop_while_negative(values):
    index = 0
    while index < len(values) and values[index] < 0:
        index += 1
    return list(values[index:])
''',
        [ok([-1, -2, 3]), ok([1, -1])],
        [ok([]), ok([-5])],
        [ok([0, -1])],
    ),
    T(
        "dev_026",
        "partition_parity",
        "intlist",
        "Implement partition_parity(values). Return a tuple of two lists, even values first and odd values second, both in their original order.",
        '''def partition_parity(values):
    evens = [value for value in values if value % 2 == 0]
    odds = [value for value in values if value % 2 != 0]
    return (evens, odds)
''',
        [ok([1, 2, 3, 4]), ok([])],
        [ok([2, 4]), ok([-1, -2])],
        [ok([0])],
        ["Return a tuple, not a list, and do not reorder within each group."],
    ),
    T(
        "dev_027",
        "count_by_name",
        "records",
        "Implement count_by_name(records). Return a dict mapping each name to how many records carry it; records without a name are skipped.",
        '''def count_by_name(records):
    counts = {}
    for record in records:
        name = record.get("name")
        if name is None:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts
''',
        [ok([{"name": "a"}, {"name": "a"}]), ok([])],
        [ok([{"name": "a"}, {"score": 1}]), ok([{"score": 2}])],
        [ok([{"name": "z"}])],
    ),
    T(
        "dev_028",
        "invert_mapping",
        "mapping",
        "Implement invert_mapping(mapping). Swap keys and values; when several keys share a value, the last one in iteration order wins.",
        '''def invert_mapping(mapping):
    return {value: key for key, value in mapping.items()}
''',
        [ok({"a": "b"}), ok({})],
        [ok({"a": "x", "b": "y"}), ok({"a": "x", "b": "x"})],
        [ok({"k": "v"})],
    ),
    T(
        "dev_029",
        "filter_by_score",
        "records_min",
        "Implement filter_by_score(records, minimum). Return the records whose score is at least minimum, preserving order; a missing score counts as zero.",
        '''def filter_by_score(records, minimum):
    return [record for record in records if record.get("score", 0) >= minimum]
''',
        [ok([{"score": 3}, {"score": 1}], 2), ok([], 5)],
        [ok([{"name": "a"}], 1), ok([{"score": 5}], 5)],
        [ok([{"score": 9}], 0)],
    ),
    T(
        "dev_030",
        "sort_records",
        "records_int",
        "Implement sort_records(records). Return the records sorted by score ascending, then by name ascending; do not mutate the input.",
        '''def sort_records(records):
    return sorted(records, key=lambda record: (record.get("score", 0), record.get("name", "")))
''',
        [ok([{"name": "b", "score": 2}, {"name": "a", "score": 1}]), ok([])],
        [ok([{"name": "b", "score": 1}, {"name": "a", "score": 1}]), ok([{"name": "z"}])],
        [ok([{"name": "a", "score": 5}])],
        ["Sorting is stable and the input list is left unchanged."],
    ),
    T(
        "dev_031",
        "pluck",
        "records_int",
        "Implement pluck(records). Return the name of every record in order, using None where a record has no name.",
        '''def pluck(records):
    return [record.get("name") for record in records]
''',
        [ok([{"name": "a"}, {"name": "b"}]), ok([])],
        [ok([{"name": "a"}, {"score": 1}]), ok([{"score": 2}])],
        [ok([{"name": "q"}])],
    ),
    T(
        "dev_032",
        "bucket_counts",
        "list_width",
        "Implement bucket_counts(values, width). Return bucket sizes for buckets [0, width), [width, 2*width), ...; an empty input gives an empty list. Width is positive.",
        '''def bucket_counts(values, width):
    if not values:
        return []
    buckets = [0] * (max(values) // width + 1)
    for value in values:
        buckets[value // width] += 1
    return buckets
''',
        [ok([0, 1, 5], 2), ok([], 3)],
        [ok([4], 2), ok([0, 0], 1)],
        [ok([6, 7], 3)],
    ),
    T(
        "dev_033",
        "binary_to_int",
        "binary",
        "Implement binary_to_int(text). Parse a non-empty string of 0 and 1 characters; raise ValueError for an empty string or any other character.",
        '''def binary_to_int(text):
    if not text or any(ch not in "01" for ch in text):
        raise ValueError("not a binary string")
    return int(text, 2)
''',
        [ok("101"), bad("ValueError", "")],
        [ok("0"), bad("ValueError", "102")],
        [ok("1")],
    ),
    T(
        "dev_034",
        "int_to_binary",
        "smallint",
        "Implement int_to_binary(n). Return the binary representation of a non-negative integer without a prefix; raise ValueError for negatives.",
        '''def int_to_binary(n):
    if n < 0:
        raise ValueError("negative values have no binary form here")
    return format(n, "b")
''',
        [ok(5), ok(0)],
        [bad("ValueError", -1), ok(8)],
        [ok(1)],
    ),
    T(
        "dev_035",
        "hex_to_rgb",
        "hexcolor",
        "Implement hex_to_rgb(text). Accept an optional leading # followed by six hex digits and return a tuple of three integers; raise ValueError for any other shape.",
        '''def hex_to_rgb(text):
    value = text[1:] if text.startswith("#") else text
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError("expected six hex digits")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
''',
        [ok("#ff0000"), bad("ValueError", "xyz")],
        [ok("00ff00"), bad("ValueError", "#fff")],
        [ok("#000000")],
    ),
    T(
        "dev_036",
        "rgb_to_hex",
        "rgb",
        "Implement rgb_to_hex(r, g, b). Return a lowercase #rrggbb string; raise ValueError when any channel is outside 0..255.",
        '''def rgb_to_hex(r, g, b):
    if any(not 0 <= channel <= 255 for channel in (r, g, b)):
        raise ValueError("channel outside 0..255")
    return "#{:02x}{:02x}{:02x}".format(r, g, b)
''',
        [ok(255, 0, 16), bad("ValueError", 256, 0, 0)],
        [ok(0, 0, 0), bad("ValueError", 0, -1, 0)],
        [ok(1, 2, 3)],
    ),
    T(
        "dev_037",
        "is_valid_ipv4",
        "ipv4ish",
        "Implement is_valid_ipv4(text). Return True only for four dot-separated decimal parts in 0..255 with no leading zeros (a single 0 is fine).",
        '''def is_valid_ipv4(text):
    parts = text.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part or not part.isdigit():
            return False
        if len(part) > 1 and part[0] == "0":
            return False
        if int(part) > 255:
            return False
    return True
''',
        [ok("127.0.0.1"), ok("1.2.3")],
        [ok("0.0.0.0"), ok("01.2.3.4")],
        [ok("255.255.255.255")],
    ),
    T(
        "dev_038",
        "weekday_abbrev",
        "weekday",
        "Implement weekday_abbrev(name). Return the three-letter abbreviation Mon..Sun for a case-insensitive English weekday name; raise ValueError for anything else.",
        '''def weekday_abbrev(name):
    days = {
        "monday": "Mon",
        "tuesday": "Tue",
        "wednesday": "Wed",
        "thursday": "Thu",
        "friday": "Fri",
        "saturday": "Sat",
        "sunday": "Sun",
    }
    try:
        return days[name.lower()]
    except KeyError:
        raise ValueError("not a weekday name") from None
''',
        [ok("Monday"), bad("ValueError", "Funday")],
        [ok("WEDNESDAY"), ok("sunday")],
        [ok("friday")],
    ),
    T(
        "dev_039",
        "parse_ints",
        "int_csv_ok",
        "Implement parse_ints(text). Split on commas, strip whitespace, skip empty fields and return integers; raise ValueError when a field is not an integer.",
        '''def parse_ints(text):
    result = []
    for field in text.split(","):
        field = field.strip()
        if not field:
            continue
        result.append(int(field))
    return result
''',
        [ok("1,2"), bad("ValueError", "1,a")],
        [ok(""), ok(" 4 ,5 ")],
        [ok("7,8,9")],
    ),
    T(
        "dev_040",
        "wrap_text",
        "text_width",
        "Implement wrap_text(text, width). Greedily pack whitespace-separated words into lines of at most width characters, keeping a word longer than width on its own line; an empty input gives an empty list.",
        '''def wrap_text(text, width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = current + " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
''',
        [ok("a b c", 3), ok("", 5)],
        [ok("hello world", 5), ok("abcdef", 3)],
        [ok("one two", 7)],
    ),
]
