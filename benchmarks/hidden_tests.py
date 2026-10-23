"""Held-out scoring checks for the fixed benchmark corpus.

Do not add this module to a model prompt. The benchmark runner invokes it only
as an evaluator after a candidate has been produced. Every assertion states an
edge case that the task description or invariants already promise.
"""

from __future__ import annotations

import sys

from task_runner import load_module, load_solution


def _check(task_id: str, m) -> None:
    checks = {
        "task_001": lambda: _eq(m.count_vowels("rhythms"), 0) and _eq(m.count_vowels("AEIOUaeiou"), 10) and _eq(m.count_vowels(""), 0),
        "task_002": lambda: _eq(m.is_palindrome(""), True) and _eq(m.is_palindrome("No lemon, no melon!"), True) and _eq(m.is_palindrome("0P"), False),
        "task_003": lambda: _eq(m.reverse_words("  alpha   beta "), "beta alpha") and _eq(m.reverse_words(""), "") and _eq(m.reverse_words("   "), ""),
        "task_004": lambda: _eq(m.run_length_encode(""), "") and _eq(m.run_length_encode("bookkeeper"), "b1o2k2e2p1e1r1") and _eq(m.run_length_encode("zzz"), "z3"),
        "task_005": lambda: _eq(m.chunk([], 3), []) and _eq(m.chunk([1, 2, 3], 5), [[1, 2, 3]]) and _raises(ValueError, m.chunk, [1], 0),
        "task_006": lambda: _eq(m.merge_sorted([-3, 0, 4], [-2, 0, 9]), [-3, -2, 0, 0, 4, 9]) and _eq(m.merge_sorted([2, 2], [2]), [2, 2, 2]),
        "task_007": lambda: _eq(m.rotate([1, 2, 3, 4], 6), [3, 4, 1, 2]) and _eq(m.rotate([1, 2, 3], -1), [2, 3, 1]) and _eq(m.rotate([], 2), []),
        "task_008": lambda: _eq(m.unique_preserve(["a", "b", "a", "a", "c"]), ["a", "b", "c"]) and _eq(m.unique_preserve([1, "1", 1]), [1, "1"]),
        "task_009": lambda: _eq(m.flatten_once([(1, 2), [3], "xy"]), [1, 2, 3, "x", "y"]) and _eq(m.flatten_once([["a"], ["b", "c"]]), ["a", "b", "c"]),
        "task_010": lambda: _eq(m.group_anagrams(["abc", "bca", "Cab", "foo"]), {"abc": ["abc", "bca", "Cab"], "foo": ["foo"]}) and _eq(m.group_anagrams(["", ""]), {"": ["", ""]}),
        "task_011": lambda: _eq(m.top_k_frequent([4, 5, 4, 5, 6], 2), [4, 5]) and _eq(m.top_k_frequent([2, 2, 1, 1], 2), [2, 1]) and _eq(m.top_k_frequent([1, 2], 0), []),
        "task_012": lambda: _eq(m.balanced_brackets("([{}])"), True) and _eq(m.balanced_brackets("([)]"), False) and _eq(m.balanced_brackets("((( "), False),
        "task_013": lambda: _eq(m.camel_to_snake("HTTPRequest"), "http_request") and _eq(m.camel_to_snake("already_snake"), "already_snake") and _eq(m.camel_to_snake("_Leading__Underscore_"), "leading_underscore"),
        "task_014": lambda: _eq(m.parse_query("q=hello%20world&flag=&q=again"), {"q": ["hello world", "again"], "flag": [""]}) and _eq(m.parse_query("a+b=c+d"), {"a b": ["c d"]}),
        "task_015": lambda: _eq(m.roman_to_int("IV"), 4) and _eq(m.roman_to_int("XLII"), 42) and _raises(ValueError, m.roman_to_int, "IIII"),
        "task_016": lambda: _eq(m.int_to_roman(1), "I") and _eq(m.int_to_roman(3999), "MMMCMXCIX") and _raises(ValueError, m.int_to_roman, 0),
        "task_017": lambda: _eq(m.gcd_many([0, -24, 36]), 12) and _eq(m.gcd_many([0, 5]), 5) and _raises(ValueError, m.gcd_many, []),
        "task_018": lambda: _eq(m.lcm_many([0, 6]), 0) and _eq(m.lcm_many([-4, 6]), 12) and _eq(m.lcm_many([2]), 2) and _raises(ValueError, m.lcm_many, []),
        "task_019": lambda: _eq(m.is_prime(1), False) and _eq(m.is_prime(0), False) and _eq(m.is_prime(2), True) and _eq(m.is_prime(221), False),
        "task_020": lambda: _eq(m.fibonacci(0), 0) and _eq(m.fibonacci(1), 1) and _eq(m.fibonacci(2), 1) and _raises(ValueError, m.fibonacci, -1),
        "task_021": lambda: _eq(m.binary_search([], 3), -1) and _eq(m.binary_search([1, 2, 2, 2, 4], 2), 1) and _eq(m.binary_search([5], 1), -1) and _eq(m.binary_search([1, 2], 9), -1),
        "task_022": lambda: _eq(m.longest_common_prefix([]), "") and _eq(m.longest_common_prefix([""]), "") and _eq(m.longest_common_prefix(["dog", "racecar"]), "") and _eq(m.longest_common_prefix(["flower", "flow", "flight"]), "fl"),
        "task_023": lambda: _eq(m.levenshtein_distance("", "abc"), 3) and _eq(m.levenshtein_distance("a", ""), 1) and _eq(m.levenshtein_distance("same", "same"), 0),
        "task_024": lambda: _eq(m.transpose([]), []) and _eq(m.transpose([[1, 2]]), [[1], [2]]) and _raises(ValueError, m.transpose, [[1], [2, 3]]),
        "task_025": lambda: _eq(m.spiral_order([[1, 2, 3, 4], [5, 6, 7, 8]]), [1, 2, 3, 4, 8, 7, 6, 5]) and _eq(m.spiral_order([[1, 2], [3, 4]]), [1, 2, 4, 3]) and _eq(m.spiral_order([]), []),
        "task_026": lambda: _eq(m.matrix_multiply([[1, 2, 3]], [[4], [5], [6]]), [[32]]) and _eq(m.matrix_multiply([[1], [2]], [[3, 4]]), [[3, 4], [6, 8]]) and _raises(ValueError, m.matrix_multiply, [[1, 2]], [[1, 2]]),
        "task_027": lambda: _eq(m.merge_intervals([[5, 7], [1, 2], [2, 5], [10, 10]]), [[1, 7], [10, 10]]) and _eq(m.merge_intervals([[1, 2], [2, 3]]), [[1, 3]]),
        "task_028": lambda: _eq(m.evaluate_rpn(["5", "2", "/"]), 2) and _eq(m.evaluate_rpn(["-7", "2", "/"]), -3) and _eq(m.evaluate_rpn(["10", "3", "-"]), 7) and _raises(ValueError, m.evaluate_rpn, ["2", "+"]),
        "task_029": lambda: _eq(m.format_duration(0), "0s") and _eq(m.format_duration(60), "1m") and _eq(m.format_duration(3661), "1h 1m 1s") and _raises(ValueError, m.format_duration, -1),
        "task_030": lambda: _eq(
            m.stable_sort_records(
                [{"name": "first", "score": 2}, {"name": "second", "score": 1}, {"name": "third", "score": 2}],
                "score",
            ),
            [{"name": "second", "score": 1}, {"name": "first", "score": 2}, {"name": "third", "score": 2}],
        ) and _eq(m.stable_sort_records([{"name": "a", "score": 2}, {"name": "b", "score": 2}, {"name": "c", "score": 0}], "score"), [{"name": "c", "score": 0}, {"name": "a", "score": 2}, {"name": "b", "score": 2}]),
        "task_031": lambda: _eq(m.parse_ini("; note\n# other\n\n[x]\n a = 1 \n"), {"x": {"a": "1"}}) and _eq(m.parse_ini("[a]\nx=1\n[a]\ny=2"), {"a": {"x": "1", "y": "2"}}) and _eq(m.parse_ini("[a]\nurl = x=1"), {"a": {"url": "x=1"}}) and _raises(ValueError, m.parse_ini, "[a]\noops\n") and _raises(ValueError, m.parse_ini, "[a]\n=1\n"),
        "task_032": lambda: _eq(m.slugify("  Foo__Bar  "), "foo-bar") and _eq(m.slugify("Café au lait"), "caf-au-lait") and _eq(m.slugify("2026 Report"), "2026-report") and _eq(m.slugify(""), ""),
        "task_033": lambda: _eq(m.parse_size("2 b"), 2) and _eq(m.parse_size("0.5 KB"), 512) and _raises(ValueError, m.parse_size, "10 TB") and _raises(ValueError, m.parse_size, "10"),
        "task_034": lambda: _eq(m.wrap_text("", 5), []) and _eq(m.wrap_text("a b c", 1), ["a", "b", "c"]) and _eq(m.wrap_text("abcdefgh ij", 4), ["abcdefgh", "ij"]) and _eq(m.wrap_text("one two", 20), ["one two"]),
        "task_035": lambda: _eq(m.parse_csv_line('"say ""hi""",x'), ['say "hi"', "x"]) and _eq(m.parse_csv_line(""), [""]) and _eq(m.parse_csv_line("  a  , b "), ["a", "b"]) and _raises(ValueError, m.parse_csv_line, '"abc'),
        "task_036": lambda: _eq(m.deep_merge({"a": [1, 2]}, {"a": [3]}), {"a": [3]}) and _eq(m.deep_merge({}, {"a": 1}), {"a": 1}) and _deep_merge_is_pure(m) and _eq(load_module("task_036", "merge_utils").merge_lists([], []), []),
        "task_037": lambda: _eq(m.normalize_path("/a/b/../c/"), "/a/c") and _eq(m.normalize_path("../a/../../b"), "../../b") and _eq(m.normalize_path("/"), "/") and _eq(m.normalize_path("a/./b"), "a/b"),
        "task_038": lambda: _eq(m.intersect_intervals([[1, 2]], [[2, 3]]), [[2, 2]]) and _eq(m.intersect_intervals([], [[1, 2]]), []) and _eq(m.intersect_intervals([[1, 5]], [[5, 9]]), [[5, 5]]),
        "task_039": lambda: _eq(m.parse_duration("2d 3h"), 183600) and _eq(m.parse_duration("45s"), 45) and _eq(m.parse_duration("1M"), 60) and _raises(ValueError, m.parse_duration, "1h1h") and _raises(ValueError, m.parse_duration, "10x"),
        "task_040": lambda: _eq(m.top_words("", 3), []) and _eq(m.top_words("a b a B", 1), [("a", 2)]) and _eq(m.top_words("b a", 5), [("a", 1), ("b", 1)]) and _eq(m.top_words("x", 0), []),
        "task_041": lambda: _eq(m.compare_versions("2.10.0", "2.9.9"), 1) and _eq(m.compare_versions("1.0.0", "1.0.0"), 0) and _raises(ValueError, m.compare_versions, "1.x", "1.0") and _raises(ValueError, m.compare_versions, "1.", "1"),
        "task_042": lambda: _eq(m.safe_divide(1, 0), 0.0) and _eq(m.safe_divide(9, 2), 4.5) and _eq(m.percentage(1, 0), 0.0) and _eq(m.percentage(1, 3), 33.3),
        "task_043": lambda: _eq(m.decode_rle(""), "") and _eq(m.decode_rle("z10"), "z" * 10) and _eq(m.decode_rle("a1"), "a") and _raises(ValueError, m.decode_rle, "a0"),
        "task_044": lambda: _eq(m.to_base(0, 2), "0") and _eq(m.to_base(-10, 2), "-1010") and _eq(m.to_base(35, 36), "z") and _eq(m.from_base("-1010", 2), -10) and _eq(m.from_base("0", 10), 0) and _raises(ValueError, m.from_base, "2", 2),
        "task_045": lambda: _eq(m.summarize("a b", 5), "a b") and _eq(m.summarize(" a b c ", 2), "a b ...") and _raises(ValueError, m.summarize, "x", 0) and _eq(load_module("task_045", "text_utils").word_count(""), 0) and _eq(load_module("task_045", "text_utils").normalize_whitespace(""), ""),
        "task_046": lambda: _eq(m.moving_average([], 3), []) and _eq(m.moving_average([1], 1), [1.0]) and _eq(m.moving_average([1, 2, 3], 3), [2.0]) and _eq(m.moving_average([2, 4], 2), [3.0]),
        "task_047": lambda: _eq(m.group_by([], "k"), {}) and _eq(m.group_by([{"k": "x"}], "k"), {"x": [{"k": "x"}]}) and _eq(m.group_by([{"k": "b", "n": 1}, {"k": "b", "n": 2}], "k"), {"b": [{"k": "b", "n": 1}, {"k": "b", "n": 2}]}),
        "task_048": lambda: _eq(load_module("task_048", "tokens").bigrams("one"), []) and _eq(load_module("task_048", "tokens").bigrams(""), []) and _eq(m.jaccard("", ""), 1.0) and _eq(m.jaccard("a b", "c d"), 0.0) and _eq(m.jaccard("a b c", "a b c"), 1.0),
        "task_049": lambda: _eq(m.total_area([]), 0) and _eq(m.overlap_area({"x": 0, "y": 0, "w": 1, "h": 1}, {"x": 2, "y": 2, "w": 1, "h": 1}), 0) and _eq(m.overlap_area({"x": 0, "y": 0, "w": 1, "h": 1}, {"x": 1, "y": 0, "w": 1, "h": 1}), 0) and _eq(m.overlap_area({"x": 0, "y": 0, "w": 3, "h": 2}, {"x": 0, "y": 0, "w": 3, "h": 2}), 6),
        "task_050": lambda: _eq(m.compress_ranges([3, 1, 2, 2]), "1-3") and _eq(m.compress_ranges([1, 2, 4, 5]), "1,2,4,5") and _eq(m.compress_ranges([7]), "7") and _eq(m.compress_ranges([-2, -1, 0, 5]), "-2-0,5"),
    }
    checks[task_id]()


def _deep_merge_is_pure(m) -> bool:
    base = {"a": {"b": 1}, "keep": True}
    merged = m.deep_merge(base, {"a": {"c": 2}})
    _eq(base, {"a": {"b": 1}, "keep": True})
    _eq(merged, {"a": {"b": 1, "c": 2}, "keep": True})
    return True


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
        _check(task_id, load_solution(task_id))
    except Exception as exc:  # noqa: BLE001 - evaluator output is intentionally the only retry signal
        print(f"hidden test failed for {task_id}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
