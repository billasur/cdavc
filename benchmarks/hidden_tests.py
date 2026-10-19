"""Held-out scoring checks for the fixed benchmark corpus.

Do not add this module to a model prompt. The benchmark runner invokes it only
as an evaluator after a candidate has been produced.
"""

from __future__ import annotations

import sys

from task_runner import load_solution


def _check(task_id: str, m) -> None:
    checks = {
        "task_001": lambda: _eq(m.count_vowels("rhythms"), 0) and _eq(m.count_vowels("AEIOUaeiou"), 10),
        "task_002": lambda: _eq(m.is_palindrome(""), True) and _eq(m.is_palindrome("No lemon, no melon!"), True) and _eq(m.is_palindrome("robot"), False),
        "task_003": lambda: _eq(m.reverse_words("  alpha   beta "), "beta alpha") and _eq(m.reverse_words(""), ""),
        "task_004": lambda: _eq(m.run_length_encode(""), "") and _eq(m.run_length_encode("bookkeeper"), "b1o2k2e2p1e1r1"),
        "task_005": lambda: _eq(m.chunk([], 3), []) and _raises(ValueError, m.chunk, [1], 0),
        "task_006": lambda: _eq(m.merge_sorted([-3, 0, 4], [-2, 0, 9]), [-3, -2, 0, 0, 4, 9]),
        "task_007": lambda: _eq(m.rotate([1, 2, 3, 4], 6), [3, 4, 1, 2]) and _eq(m.rotate([], 2), []),
        "task_008": lambda: _eq(m.unique_preserve(["a", "b", "a", "a", "c"]), ["a", "b", "c"]),
        "task_009": lambda: _eq(m.flatten_once([(1, 2), [3], "xy"]), [1, 2, 3, "x", "y"]),
        "task_010": lambda: _eq(m.group_anagrams(["abc", "bca", "Cab", "foo"]), {"abc": ["abc", "bca", "Cab"], "foo": ["foo"]}),
        "task_011": lambda: _eq(m.top_k_frequent([4, 5, 4, 5, 6], 2), [4, 5]) and _eq(m.top_k_frequent([1, 2], 0), []),
        "task_012": lambda: _eq(m.balanced_brackets("([{}])"), True) and _eq(m.balanced_brackets("([)]"), False) and _eq(m.balanced_brackets("text ]"), False),
        "task_013": lambda: _eq(m.camel_to_snake("HTTPRequest"), "http_request") and _eq(m.camel_to_snake("already_snake"), "already_snake"),
        "task_014": lambda: _eq(m.parse_query("q=hello%20world&flag=&q=again"), {"q": ["hello world", "again"], "flag": [""]}),
        "task_015": lambda: _eq(m.roman_to_int("IV"), 4) and _raises(ValueError, m.roman_to_int, "IIII"),
        "task_016": lambda: _eq(m.int_to_roman(1), "I") and _eq(m.int_to_roman(3999), "MMMCMXCIX") and _raises(ValueError, m.int_to_roman, 0),
        "task_017": lambda: _eq(m.gcd_many([0, -24, 36]), 12) and _raises(ValueError, m.gcd_many, []),
        "task_018": lambda: _eq(m.lcm_many([0, 6]), 0) and _eq(m.lcm_many([-4, 6]), 12) and _raises(ValueError, m.lcm_many, []),
        "task_019": lambda: _eq(m.is_prime(1), False) and _eq(m.is_prime(2), True) and _eq(m.is_prime(221), False),
        "task_020": lambda: _eq(m.fibonacci(0), 0) and _eq(m.fibonacci(1), 1) and _raises(ValueError, m.fibonacci, -1),
        "task_021": lambda: _eq(m.binary_search([], 3), -1) and _eq(m.binary_search([1, 2, 2, 2, 4], 2), 1) and _eq(m.binary_search([1, 2], 9), -1),
        "task_022": lambda: _eq(m.longest_common_prefix([]), "") and _eq(m.longest_common_prefix(["dog", "racecar"]), "") and _eq(m.longest_common_prefix(["flower", "flow", "flight"]), "fl"),
        "task_023": lambda: _eq(m.levenshtein_distance("", "abc"), 3) and _eq(m.levenshtein_distance("same", "same"), 0),
        "task_024": lambda: _eq(m.transpose([]), []) and _raises(ValueError, m.transpose, [[1], [2, 3]]),
        "task_025": lambda: _eq(m.spiral_order([[1, 2, 3, 4], [5, 6, 7, 8]]), [1, 2, 3, 4, 8, 7, 6, 5]),
        "task_026": lambda: _eq(m.matrix_multiply([[1, 2, 3]], [[4], [5], [6]]), [[32]]) and _raises(ValueError, m.matrix_multiply, [[1, 2]], [[1, 2]]),
        "task_027": lambda: _eq(m.merge_intervals([[5, 7], [1, 2], [2, 5], [10, 10]]), [[1, 7], [10, 10]]),
        "task_028": lambda: _eq(m.evaluate_rpn(["5", "2", "/"]), 2) and _eq(m.evaluate_rpn(["-7", "2", "/"]), -3) and _raises(ValueError, m.evaluate_rpn, ["2", "+"]),
        "task_029": lambda: _eq(m.format_duration(0), "0s") and _eq(m.format_duration(60), "1m") and _raises(ValueError, m.format_duration, -1),
        "task_030": lambda: _eq(
            m.stable_sort_records(
                [{"name": "first", "score": 2}, {"name": "second", "score": 1}, {"name": "third", "score": 2}],
                "score",
            ),
            [{"name": "second", "score": 1}, {"name": "first", "score": 2}, {"name": "third", "score": 2}],
        ),
    }
    checks[task_id]()


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
