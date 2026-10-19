"""Regression evaluator for task_h6_03_circuit_breaker. Usage: python regression_tests.py [path/to/solution.py]
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
    cb = m.CircuitBreaker(1, 3)
    eq(cb.state(0), "closed")
    cb.record_failure(0)
    eq(cb.allow(1), False)

if __name__ == "__main__":
    try:
        check(load())
    except Exception as exc:  # noqa: BLE001
        print(f"regression test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
