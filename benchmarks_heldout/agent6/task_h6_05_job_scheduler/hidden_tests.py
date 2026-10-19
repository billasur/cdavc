"""Hidden evaluator for task_h6_05_job_scheduler. Usage: python hidden_tests.py [path/to/solution.py]
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
    d = {"a": 2, "b": 3, "c": 1, "d": 2}
    eq(m.schedule_jobs(d, {"c": ["a", "b"], "d": ["a"]}, 2),
       ({"a": (0, 2), "b": (0, 3), "d": (2, 4), "c": (3, 4)}, 4))
    eq(m.schedule_jobs({"b": 1, "a": 1, "c": 1}, {}, 1), ({"a": (0, 1), "b": (1, 2), "c": (2, 3)}, 3))
    eq(m.schedule_jobs({"a": 1, "b": 1}, {"a": ["b"]}, 1), ({"b": (0, 1), "a": (1, 2)}, 2))
    eq(m.schedule_jobs({}, {}, 3), ({}, 0))
    raises(ValueError, m.schedule_jobs, {"a": 1, "b": 1}, {"a": ["b"], "b": ["a"]}, 2)
    raises(ValueError, m.schedule_jobs, {"a": 1}, {"a": ["zz"]}, 1)
    raises(ValueError, m.schedule_jobs, {"a": 1}, {}, 0)
    raises(ValueError, m.schedule_jobs, {"a": 0}, {}, 1)

if __name__ == "__main__":
    try:
        check(load())
    except Exception as exc:  # noqa: BLE001
        print(f"hidden test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
