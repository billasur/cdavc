"""Independent regression checks used by the CD-AVC arm."""

from __future__ import annotations

import sys

from task_runner import load_solution


def _check(task_id: str, m) -> None:
    checks = {
        "task_001": lambda: _eq(m.count_vowels("Queue"), 4) and _eq(m.count_vowels("xyz"), 0),
        "task_002": lambda: _eq(m.is_palindrome("Was it a rat I saw?"), True) and _eq(m.is_palindrome("ab"), False),
        "task_003": lambda: _eq(m.reverse_words("one"), "one") and _eq(m.reverse_words("a  b"), "b a"),
        "task_004": lambda: _eq(m.run_length_encode("abc"), "a1b1c1") and _eq(m.run_length_encode("a"), "a1"),
        "task_005": lambda: _eq(m.chunk([1, 2, 3], 3), [[1, 2, 3]]) and _eq(m.chunk([1], 1), [[1]]),
        "task_006": lambda: _eq(m.merge_sorted([], [1]), [1]) and _eq(m.merge_sorted([1], []), [1]),
        "task_007": lambda: _eq(m.rotate([1, 2, 3], 0), [1, 2, 3]) and _eq(m.rotate([1, 2], 2), [1, 2]),
        "task_008": lambda: _eq(m.unique_preserve([]), []) and _eq(m.unique_preserve([1, 1]), [1]),
        "task_009": lambda: _eq(m.flatten_once([]), []) and _eq(m.flatten_once([[1], [2]]), [1, 2]),
        "task_010": lambda: _eq(m.group_anagrams([]), {}) and _eq(m.group_anagrams(["ba", "ab"]), {"ab": ["ba", "ab"]}),
        "task_011": lambda: _eq(m.top_k_frequent([1], 1), [1]) and _eq(m.top_k_frequent([], 3), []),
        "task_012": lambda: _eq(m.balanced_brackets(""), True) and _eq(m.balanced_brackets("]"), False),
        "task_013": lambda: _eq(m.camel_to_snake("URLValue"), "url_value") and _eq(m.camel_to_snake("a"), "a"),
        "task_014": lambda: _eq(m.parse_query(""), {}) and _eq(m.parse_query("a=1"), {"a": ["1"]}),
        "task_015": lambda: _eq(m.roman_to_int("IX"), 9) and _eq(m.roman_to_int("I"), 1),
        "task_016": lambda: _eq(m.int_to_roman(9), "IX") and _eq(m.int_to_roman(44), "XLIV"),
        "task_017": lambda: _eq(m.gcd_many([7]), 7) and _eq(m.gcd_many([12, 8]), 4),
        "task_018": lambda: _eq(m.lcm_many([7]), 7) and _eq(m.lcm_many([3, 5]), 15),
        "task_019": lambda: _eq(m.is_prime(97), True) and _eq(m.is_prime(9), False),
        "task_020": lambda: _eq(m.fibonacci(2), 1) and _eq(m.fibonacci(3), 2),
        "task_021": lambda: _eq(m.binary_search([2], 2), 0) and _eq(m.binary_search([1, 3], 3), 1),
        "task_022": lambda: _eq(m.longest_common_prefix(["same", "same"]), "same") and _eq(m.longest_common_prefix(["a"]), "a"),
        "task_023": lambda: _eq(m.levenshtein_distance("a", "b"), 1) and _eq(m.levenshtein_distance("ab", "abc"), 1),
        "task_024": lambda: _eq(m.transpose([[1]]), [[1]]) and _eq(m.transpose([[1, 2]]), [[1], [2]]),
        "task_025": lambda: _eq(m.spiral_order([[1]]), [1]) and _eq(m.spiral_order([[1, 2]]), [1, 2]),
        "task_026": lambda: _eq(m.matrix_multiply([[2]], [[3]]), [[6]]) and _eq(m.matrix_multiply([[1, 0]], [[0], [1]]), [[0]]),
        "task_027": lambda: _eq(m.merge_intervals([]), []) and _eq(m.merge_intervals([[4, 4]]), [[4, 4]]),
        "task_028": lambda: _eq(m.evaluate_rpn(["3", "4", "-"]), -1) and _eq(m.evaluate_rpn(["7"]), 7),
        "task_029": lambda: _eq(m.format_duration(86400), "1d") and _eq(m.format_duration(3600), "1h"),
        "task_030": lambda: _eq(m.stable_sort_records([], "score"), []) and _eq(m.stable_sort_records([{"score": 1}], "score"), [{"score": 1}]),
        "task_031": lambda: _eq(m.parse_ini(""), {}) and _eq(m.parse_ini("[a]\n"), {"a": {}}),
        "task_032": lambda: _eq(m.slugify("Already Slugs"), "already-slugs") and _eq(m.slugify("a"), "a"),
        "task_033": lambda: _eq(m.parse_size("1 GB"), 1073741824) and _eq(m.parse_size("1kb"), 1024),
        "task_034": lambda: _eq(m.wrap_text("abc", 3), ["abc"]) and _eq(m.wrap_text("  a  ", 5), ["a"]),
        "task_035": lambda: _eq(m.parse_csv_line(","), ["", ""]) and _eq(m.parse_csv_line("a"), ["a"]),
        "task_036": lambda: _eq(m.deep_merge({"a": 1}, {"b": 2}), {"a": 1, "b": 2}) and _eq(m.deep_merge({}, {}), {}),
        "task_037": lambda: _eq(m.normalize_path("."), ".") and _eq(m.normalize_path("a/"), "a"),
        "task_038": lambda: _eq(m.intersect_intervals([[1, 2]], [[10, 12]]), []) and _eq(m.intersect_intervals([[1, 4]], [[2, 4]]), [[2, 4]]),
        "task_039": lambda: _eq(m.parse_duration("1m"), 60) and _eq(m.parse_duration("1d"), 86400),
        "task_040": lambda: _eq(m.top_words("B a", 2), [("a", 1), ("b", 1)]) and _eq(m.top_words("a a b", 1), [("a", 2)]),
        "task_041": lambda: _eq(m.compare_versions("0.1", "0.0.1"), 1) and _eq(m.compare_versions("1.2", "1.2.0.0"), 0),
        "task_042": lambda: _eq(m.percentage(2, 5), 40.0) and _eq(m.safe_divide(0, 5), 0.0),
        "task_043": lambda: _eq(m.decode_rle("x2"), "xx") and _eq(m.decode_rle("ab1"), "ab"),
        "task_044": lambda: _eq(m.from_base("z", 36), 35) and _eq(m.to_base(10, 10), "10"),
        "task_045": lambda: _eq(m.summarize("only", 1), "only") and _eq(m.summarize("a b c", 3), "a b c"),
        "task_046": lambda: _eq(m.moving_average([5], 2), []) and _eq(m.moving_average([4, 4], 2), [4.0]),
        "task_047": lambda: _eq(m.group_by([{"k": "z"}, {"k": "z"}], "k"), {"z": [{"k": "z"}, {"k": "z"}]}) and _eq(m.group_by([{"k": 1}], "k"), {1: [{"k": 1}]}),
        "task_048": lambda: _eq(m.jaccard("a b", "a c"), 0.0) and _eq(m.jaccard("a b", "a b"), 1.0),
        "task_049": lambda: _eq(m.overlap_area({"x": 0, "y": 0, "w": 2, "h": 2}, {"x": 0, "y": 0, "w": 2, "h": 2}), 4) and _eq(m.total_area([{"x": 1, "y": 1, "w": 1, "h": 1}]), 1),
        "task_050": lambda: _eq(m.compress_ranges([1, 3]), "1,3") and _eq(m.compress_ranges([1, 2, 3]), "1-3"),
    }
    checks[task_id]()


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def main(argv: list[str] | None = None) -> int:
    task_id = (argv or sys.argv[1:])[0]
    try:
        _check(task_id, load_solution(task_id))
    except Exception as exc:  # noqa: BLE001 - regression failures are gate data
        print(f"regression test failed for {task_id}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
