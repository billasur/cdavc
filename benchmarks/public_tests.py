"""Public smoke checks for the fixed CD-AVC benchmark corpus.

The model is not given this file by the harness. It exists to make the cage's
targeted gate distinct from the held-out score, so every assertion here states
a behaviour the task description or invariants already promise.
"""

from __future__ import annotations

import sys

from task_runner import load_module, load_solution


def _tests():
    return {
        "task_001": lambda m: _eq(m.count_vowels("Hello, World!"), 3) and _eq(m.count_vowels("rhythms"), 0),
        "task_002": lambda m: _eq(m.is_palindrome("A man, a plan, a canal: Panama"), True) and _eq(m.is_palindrome("robot"), False),
        "task_003": lambda m: _eq(m.reverse_words("one two three"), "three two one") and _eq(m.reverse_words("  alpha   beta "), "beta alpha"),
        "task_004": lambda m: _eq(m.run_length_encode("aaabbc"), "a3b2c1") and _eq(m.run_length_encode(""), ""),
        "task_005": lambda m: _eq(m.chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]) and _eq(m.chunk([], 3), []) and _raises(ValueError, m.chunk, [1], 0),
        "task_006": lambda m: _eq(m.merge_sorted([1, 3, 5], [2, 4, 6]), [1, 2, 3, 4, 5, 6]) and _eq(m.merge_sorted([], [1]), [1]),
        "task_007": lambda m: _eq(m.rotate([1, 2, 3, 4], 1), [4, 1, 2, 3]) and _eq(m.rotate([1, 2, 3, 4], 6), [3, 4, 1, 2]) and _eq(m.rotate([], 2), []),
        "task_008": lambda m: _eq(m.unique_preserve([3, 1, 3, 2, 1]), [3, 1, 2]) and _eq(m.unique_preserve([]), []),
        "task_009": lambda m: _eq(m.flatten_once([[1, 2], [], [3]]), [1, 2, 3]) and _eq(m.flatten_once([]), []),
        "task_010": lambda m: _eq(m.group_anagrams(["eat", "Tea", "tan"]), {"aet": ["eat", "Tea"], "ant": ["tan"]}) and _eq(m.group_anagrams([]), {}),
        "task_011": lambda m: _eq(m.top_k_frequent([1, 1, 2, 3, 3, 3, 2], 2), [3, 1]) and _eq(m.top_k_frequent([1, 2], 0), []),
        "task_012": lambda m: _eq(m.balanced_brackets("if (x[0] == 1) { return; }"), True) and _eq(m.balanced_brackets("([)]"), False),
        "task_013": lambda m: _eq(m.camel_to_snake("CamelCaseValue"), "camel_case_value") and _eq(m.camel_to_snake("HTTPRequest"), "http_request"),
        "task_014": lambda m: _eq(m.parse_query("a=1&b=two&a=3"), {"a": ["1", "3"], "b": ["two"]}) and _eq(m.parse_query(""), {}),
        "task_015": lambda m: _eq(m.roman_to_int("MCMXCIV"), 1994) and _raises(ValueError, m.roman_to_int, "IIII"),
        "task_016": lambda m: _eq(m.int_to_roman(1994), "MCMXCIV") and _raises(ValueError, m.int_to_roman, 0),
        "task_017": lambda m: _eq(m.gcd_many([84, 30, 18]), 6) and _raises(ValueError, m.gcd_many, []),
        "task_018": lambda m: _eq(m.lcm_many([4, 6, 10]), 60) and _eq(m.lcm_many([0, 6]), 0),
        "task_019": lambda m: _eq(m.is_prime(97), True) and _eq(m.is_prime(1), False),
        "task_020": lambda m: _eq(m.fibonacci(10), 55) and _raises(ValueError, m.fibonacci, -1),
        "task_021": lambda m: _eq(m.binary_search([1, 2, 2, 4, 8], 2), 1) and _eq(m.binary_search([], 3), -1),
        "task_022": lambda m: _eq(m.longest_common_prefix(["interview", "internet", "internal"]), "inter") and _eq(m.longest_common_prefix(["dog", "racecar"]), ""),
        "task_023": lambda m: _eq(m.levenshtein_distance("kitten", "sitting"), 3) and _eq(m.levenshtein_distance("", "abc"), 3),
        "task_024": lambda m: _eq(m.transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]]) and _raises(ValueError, m.transpose, [[1], [2, 3]]),
        "task_025": lambda m: _eq(m.spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), [1, 2, 3, 6, 9, 8, 7, 4, 5]) and _eq(m.spiral_order([[1]]), [1]),
        "task_026": lambda m: _eq(m.matrix_multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]]) and _raises(ValueError, m.matrix_multiply, [[1, 2]], [[1, 2]]),
        "task_027": lambda m: _eq(m.merge_intervals([[1, 3], [2, 6], [8, 10]]), [[1, 6], [8, 10]]) and _eq(m.merge_intervals([]), []),
        "task_028": lambda m: _eq(m.evaluate_rpn(["2", "1", "+", "3", "*"]), 9) and _eq(m.evaluate_rpn(["-7", "2", "/"]), -3),
        "task_029": lambda m: _eq(m.format_duration(93784), "1d 2h 3m 4s") and _eq(m.format_duration(0), "0s"),
        "task_030": lambda m: _eq(
            m.stable_sort_records([{"name": "a", "score": 2}, {"name": "b", "score": 1}], "score"),
            [{"name": "b", "score": 1}, {"name": "a", "score": 2}],
        ) and _eq(m.stable_sort_records([], "score"), []),
        "task_031": lambda m: _eq(
            m.parse_ini("[db]\nhost = localhost\nport=5432\n"),
            {"db": {"host": "localhost", "port": "5432"}},
        ) and _raises(ValueError, m.parse_ini, "host=localhost\n[db]\n"),
        "task_032": lambda m: _eq(m.slugify("Hello, World!"), "hello-world") and _eq(m.slugify("!!!"), ""),
        "task_033": lambda m: _eq(m.parse_size("10 KB"), 10240) and _eq(m.parse_size("1.5MB"), 1572864),
        "task_034": lambda m: _eq(m.wrap_text("the quick brown fox", 10), ["the quick", "brown fox"]) and _raises(ValueError, m.wrap_text, "abc", 0),
        "task_035": lambda m: _eq(m.parse_csv_line('a, "b,b", c'), ["a", "b,b", "c"]) and _raises(ValueError, m.parse_csv_line, '"abc'),
        "task_036": lambda m: _eq(m.deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"c": 3}}), {"a": {"b": 1, "c": 3}})
        and _eq(load_module("task_036", "merge_utils").merge_lists([1, 2], [2, 3]), [1, 2, 3]),
        "task_037": lambda m: _eq(m.normalize_path("a//b/./c"), "a/b/c") and _eq(m.normalize_path(""), "."),
        "task_038": lambda m: _eq(m.intersect_intervals([[1, 5], [8, 10]], [[2, 3], [9, 12]]), [[2, 3], [9, 10]]) and _eq(m.intersect_intervals([[1, 2]], [[3, 4]]), []),
        "task_039": lambda m: _eq(m.parse_duration("1h30m"), 5400) and _raises(ValueError, m.parse_duration, ""),
        "task_040": lambda m: _eq(m.top_words("the cat the dog", 2), [("the", 2), ("cat", 1)]) and _eq(m.top_words("x", 0), []),
        "task_041": lambda m: _eq(m.compare_versions("1.2.3", "1.2.4"), -1) and _eq(m.compare_versions("1.0", "1"), 0),
        "task_042": lambda m: _eq(m.safe_divide(6, 3), 2.0) and _eq(m.safe_divide(1, 0, default=-1), -1.0) and _eq(m.percentage(1, 4), 25.0),
        "task_043": lambda m: _eq(m.decode_rle("a3b2c1"), "aaabbc") and _raises(ValueError, m.decode_rle, "abc"),
        "task_044": lambda m: _eq(m.to_base(255, 16), "ff") and _eq(m.from_base("ff", 16), 255) and _raises(ValueError, m.to_base, 5, 1),
        "task_045": lambda m: _eq(m.summarize("the  quick brown fox", 2), "the quick ...")
        and _eq(load_module("task_045", "text_utils").normalize_whitespace("  a \n b "), "a b")
        and _eq(load_module("task_045", "text_utils").word_count("  a  b "), 2),
        "task_046": lambda m: _eq(m.moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5]) and _raises(ValueError, m.moving_average, [1], 0),
        "task_047": lambda m: _eq(
            m.group_by([{"k": "a"}, {"k": "b"}, {"k": "a"}], "k"),
            {"a": [{"k": "a"}, {"k": "a"}], "b": [{"k": "b"}]},
        ) and _raises(KeyError, m.group_by, [{"other": 1}], "k"),
        "task_048": lambda m: _eq(m.jaccard("a b c", "a b d"), 0.333) and _eq(load_module("task_048", "tokens").bigrams("A b C"), ["a b", "b c"]),
        "task_049": lambda m: _eq(m.total_area([{"x": 0, "y": 0, "w": 2, "h": 3}, {"x": 5, "y": 5, "w": 1, "h": 1}]), 7)
        and _eq(m.overlap_area({"x": 0, "y": 0, "w": 2, "h": 2}, {"x": 1, "y": 1, "w": 2, "h": 2}), 1),
        "task_050": lambda m: _eq(m.compress_ranges([1, 2, 3, 5]), "1-3,5") and _eq(m.compress_ranges([]), ""),
    }


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"
    return True


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return True
    raise AssertionError(f"expected {error.__name__}")


def main(argv: list[str] | None = None) -> int:
    task_id = (argv or sys.argv[1:])[0]
    try:
        _tests()[task_id](load_solution(task_id))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"public test failed for {task_id}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
