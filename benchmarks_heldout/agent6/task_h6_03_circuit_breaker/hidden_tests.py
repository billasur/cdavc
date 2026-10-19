"""Hidden evaluator for task_h6_03_circuit_breaker. Usage: python hidden_tests.py [path/to/solution.py]
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
    cb = m.CircuitBreaker(3, 10)
    for t in (0, 1):
        cb.record_failure(t)
    cb.record_success(2)
    for t in (3, 4):
        cb.record_failure(t)
    eq(cb.state(4), "closed")
    cb.record_failure(5)
    eq([cb.state(5), cb.allow(14.9), cb.state(15), cb.allow(15)], ["open", False, "half_open", True])
    cb.record_failure(15)
    eq([cb.state(24.9), cb.state(25)], ["open", "half_open"])
    cb = m.CircuitBreaker(3, 10, 2)
    for t in (0, 0, 0):
        cb.record_failure(t)
    cb.record_success(10)
    eq(cb.state(10), "half_open")
    cb.record_success(11)
    eq(cb.state(11), "closed")
    cb.record_failure(12); cb.record_failure(12)
    eq(cb.state(12), "closed")
    cb.record_failure(12)
    eq(cb.state(12), "open")
    raises(ValueError, m.CircuitBreaker, 0, 1)
    raises(ValueError, m.CircuitBreaker, 1, -1)
    raises(ValueError, m.CircuitBreaker, 1, 1, 0)

if __name__ == "__main__":
    try:
        check(load())
    except Exception as exc:  # noqa: BLE001
        print(f"hidden test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
