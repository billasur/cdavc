"""Hidden evaluator for task_h54_semver (held-out writer 5: text formats/validation)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CHECKS = [
    lambda m: _eq(m.compare_semver("1.0.0-alpha", "1.0.0"), -1),
    lambda m: _eq(m.compare_semver("1.0.0", "1.0.0-rc.1"), 1),
    lambda m: _eq(m.compare_semver("1.0.0+build1", "1.0.0+build2"), 0),
    lambda m: _eq(m.compare_semver("1.0.0-alpha.1", "1.0.0-alpha.beta"), -1),
    lambda m: _eq(m.compare_semver("1.0.0-alpha.2", "1.0.0-alpha.10"), -1),
    lambda m: _eq(m.compare_semver("1.0.0-alpha", "1.0.0-alpha.1"), -1),
    lambda m: _eq(m.compare_semver("1.0.0-beta", "1.0.0-alpha"), 1),
    lambda m: _eq(m.compare_semver("1.0.0-Beta", "1.0.0-alpha"), -1),
    lambda m: _eq(m.compare_semver("2.0.0", "10.0.0"), -1),
    lambda m: _eq(m.compare_semver("1.0.0-0.3.7", "1.0.0-0.3.7"), 0),
    lambda m: _eq(m.compare_semver("1.0.0-a-b", "1.0.0-a-c"), -1),
    lambda m: _raises(ValueError, m.compare_semver, "1.0", "1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "01.0.0", "1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0", "1.0.0-01"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0-", "1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0-a..b", "1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0", "v1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0+", "1.0.0"),
    lambda m: _raises(ValueError, m.compare_semver, "1.0.0-a_b", "1.0.0"),

]


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"
    return True


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return True
    raise AssertionError(f"expected {error.__name__}")


def _load():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "solution.py"
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        m = _load()
        for check in CHECKS:
            check(m)
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed: {exc!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
