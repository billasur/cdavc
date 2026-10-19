"""Hidden evaluator for task_h55_hexcolor (held-out writer 5: text formats/validation)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CHECKS = [
    lambda m: _eq(m.normalize_hex_color("#a1B2c3"), "#a1b2c3"),
    lambda m: _eq(m.normalize_hex_color("#11223344"), "#11223344"),
    lambda m: _eq(m.normalize_hex_color("#112233FF"), "#112233"),
    lambda m: _eq(m.normalize_hex_color("#112233Ff"), "#112233"),
    lambda m: _eq(m.normalize_hex_color("  #fff \n"), "#ffffff"),
    lambda m: _eq(m.normalize_hex_color("#000000"), "#000000"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "abc"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#ab"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#abcd"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#abcde"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#abcdefa"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#ggg"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "#12345g"),
    lambda m: _raises(ValueError, m.normalize_hex_color, ""),
    lambda m: _raises(ValueError, m.normalize_hex_color, "# fff"),
    lambda m: _raises(ValueError, m.normalize_hex_color, "##fff"),

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
