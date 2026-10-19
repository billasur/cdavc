"""Hidden evaluator for task_h51_luhn (held-out writer 5: text formats/validation)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CHECKS = [
    lambda m: _eq(m.luhn_valid("79927398713"), True),
    lambda m: _eq(m.luhn_valid("79927398710"), False),
    lambda m: _eq(m.luhn_valid("0000"), True),
    lambda m: _eq(m.luhn_valid("0"), False),
    lambda m: _eq(m.luhn_valid(""), False),
    lambda m: _eq(m.luhn_valid("1234-5678 9"), False),
    lambda m: _eq(m.luhn_valid("4111-1111-1111-1111"), True),
    lambda m: _eq(m.luhn_valid("4111x1111"), False),
    lambda m: _eq(m.luhn_valid("\t4111111111111111"), False),
    lambda m: _eq(m.luhn_valid(" - "), False),
    lambda m: _eq(m.luhn_valid("\u0664\u0661"), False),
    lambda m: _eq(m.luhn_valid("59"), True),

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
