"""Hidden evaluator for task_h6_04_reorder_buffer. Usage: python hidden_tests.py [path/to/solution.py]
Defaults to reference_solution.py in this directory. Stdlib only, deterministic."""
import importlib.util, sys
from pathlib import Path


def load():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "reference_solution.py"
    spec = importlib.util.spec_from_file_location("candidate", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def raises(error, fn, *a):
    try:
        fn(*a)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def check(m):
    eq(m.reorder([(0, "a"), (0, "X"), (1, "b")]), (["a", "b"], []))
    eq(m.reorder([(4, "old"), (5, "e"), (7, "g"), (6, "f")], 5), (["e", "f", "g"], []))
    eq(m.reorder([(2, "c"), (0, "a")]), (["a"], [2]))
    eq(m.reorder([]), ([], []))
    eq(m.reorder([(3, "d"), (3, "z")]), ([], [3]))
    eq(m.reorder([(9, "i"), (7, "g"), (8, "h"), (11, "k")], 7), (["g", "h", "i"], [11]))

if __name__ == "__main__":
    try:
        check(load())
    except Exception as exc:  # noqa: BLE001
        print(f"hidden test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
