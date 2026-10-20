"""Hidden checks for task_e12_merge_sorted_lazy (dev2 set, written without reading any held-out test)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except error:
        return
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"expected {error.__name__}, got {type(exc).__name__}: {exc}")
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
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


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e12_merge_sorted_lazy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
