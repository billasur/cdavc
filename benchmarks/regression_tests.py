"""Independent regression checks used by the CD-AVC arm."""

from __future__ import annotations

import sys

from task_runner import load_solution


def _check(task_id: str, m) -> None:
    checks = {
        "task_001": lambda: _eq(m.count_vowels("Queue"), 4),
        "task_002": lambda: _eq(m.is_palindrome("Was it a rat I saw?"), True),
        "task_003": lambda: _eq(m.reverse_words("one"), "one"),
        "task_004": lambda: _eq(m.run_length_encode("abc"), "a1b1c1"),
        "task_005": lambda: _eq(m.chunk([1, 2, 3], 3), [[1, 2, 3]]),
        "task_006": lambda: _eq(m.merge_sorted([], [1]), [1]),
        "task_007": lambda: _eq(m.rotate([1, 2, 3], 0), [1, 2, 3]),
        "task_008": lambda: _eq(m.unique_preserve([]), []),
        "task_009": lambda: _eq(m.flatten_once([]), []),
        "task_010": lambda: _eq(m.group_anagrams([]), {}),
        "task_011": lambda: _eq(m.top_k_frequent([1], 1), [1]),
        "task_012": lambda: _eq(m.balanced_brackets(""), True),
        "task_013": lambda: _eq(m.camel_to_snake("URLValue"), "url_value"),
        "task_014": lambda: _eq(m.parse_query(""), {}),
        "task_015": lambda: _eq(m.roman_to_int("IX"), 9),
        "task_016": lambda: _eq(m.int_to_roman(9), "IX"),
        "task_017": lambda: _eq(m.gcd_many([7]), 7),
        "task_018": lambda: _eq(m.lcm_many([7]), 7),
        "task_019": lambda: _eq(m.is_prime(97), True),
        "task_020": lambda: _eq(m.fibonacci(2), 1),
        "task_021": lambda: _eq(m.binary_search([2], 2), 0),
        "task_022": lambda: _eq(m.longest_common_prefix(["same", "same"]), "same"),
        "task_023": lambda: _eq(m.levenshtein_distance("a", "b"), 1),
        "task_024": lambda: _eq(m.transpose([[1]]), [[1]]),
        "task_025": lambda: _eq(m.spiral_order([[1]]), [1]),
        "task_026": lambda: _eq(m.matrix_multiply([[2]], [[3]]), [[6]]),
        "task_027": lambda: _eq(m.merge_intervals([]), []),
        "task_028": lambda: _eq(m.evaluate_rpn(["3", "4", "-"]), -1),
        "task_029": lambda: _eq(m.format_duration(86400), "1d"),
        "task_030": lambda: _eq(m.stable_sort_records([], "score"), []),
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
