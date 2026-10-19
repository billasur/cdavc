"""Public smoke checks for the fixed CD-AVC benchmark corpus.

The model is not given this file by the harness. It exists to make the cage's
targeted gate distinct from the held-out score.
"""

from __future__ import annotations

import sys

from task_runner import load_solution


def _tests():
    return {
        "task_001": lambda m: _eq(m.count_vowels("Hello, World!"), 3),
        "task_002": lambda m: _eq(m.is_palindrome("A man, a plan, a canal: Panama"), True),
        "task_003": lambda m: _eq(m.reverse_words("one two three"), "three two one"),
        "task_004": lambda m: _eq(m.run_length_encode("aaabbc"), "a3b2c1"),
        "task_005": lambda m: _eq(m.chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]),
        "task_006": lambda m: _eq(m.merge_sorted([1, 3, 5], [2, 4, 6]), [1, 2, 3, 4, 5, 6]),
        "task_007": lambda m: _eq(m.rotate([1, 2, 3, 4], 1), [4, 1, 2, 3]),
        "task_008": lambda m: _eq(m.unique_preserve([3, 1, 3, 2, 1]), [3, 1, 2]),
        "task_009": lambda m: _eq(m.flatten_once([[1, 2], [], [3]]), [1, 2, 3]),
        "task_010": lambda m: _eq(m.group_anagrams(["eat", "Tea", "tan"]), {"aet": ["eat", "Tea"], "ant": ["tan"]}),
        "task_011": lambda m: _eq(m.top_k_frequent([1, 1, 2, 3, 3, 3, 2], 2), [3, 1]),
        "task_012": lambda m: _eq(m.balanced_brackets("if (x[0] == 1) { return; }"), True),
        "task_013": lambda m: _eq(m.camel_to_snake("CamelCaseValue"), "camel_case_value"),
        "task_014": lambda m: _eq(m.parse_query("a=1&b=two&a=3"), {"a": ["1", "3"], "b": ["two"]}),
        "task_015": lambda m: _eq(m.roman_to_int("MCMXCIV"), 1994),
        "task_016": lambda m: _eq(m.int_to_roman(1994), "MCMXCIV"),
        "task_017": lambda m: _eq(m.gcd_many([84, 30, 18]), 6),
        "task_018": lambda m: _eq(m.lcm_many([4, 6, 10]), 60),
        "task_019": lambda m: _eq(m.is_prime(97), True),
        "task_020": lambda m: _eq(m.fibonacci(10), 55),
        "task_021": lambda m: _eq(m.binary_search([1, 2, 2, 4, 8], 2), 1),
        "task_022": lambda m: _eq(m.longest_common_prefix(["interview", "internet", "internal"]), "inter"),
        "task_023": lambda m: _eq(m.levenshtein_distance("kitten", "sitting"), 3),
        "task_024": lambda m: _eq(m.transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]]),
        "task_025": lambda m: _eq(m.spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), [1, 2, 3, 6, 9, 8, 7, 4, 5]),
        "task_026": lambda m: _eq(m.matrix_multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]]),
        "task_027": lambda m: _eq(m.merge_intervals([[1, 3], [2, 6], [8, 10]]), [[1, 6], [8, 10]]),
        "task_028": lambda m: _eq(m.evaluate_rpn(["2", "1", "+", "3", "*"]), 9),
        "task_029": lambda m: _eq(m.format_duration(93784), "1d 2h 3m 4s"),
        "task_030": lambda m: _eq(
            m.stable_sort_records([{"name": "a", "score": 2}, {"name": "b", "score": 1}], "score"),
            [{"name": "b", "score": 1}, {"name": "a", "score": 2}],
        ),
    }


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


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
