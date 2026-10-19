"""Held-out checks for task_d901_rle_codec. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d901_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args):
    try:
        function(*args)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    _eq(m.rle_encode(""), "")
    _eq(m.rle_decode(""), "")
    _eq(m.rle_encode("a"), "1:a")
    _eq(m.rle_encode("aa"), "2:a")
    _eq(m.rle_encode("aaaaaaaaaaa"), "11:a")
    _eq(m.rle_encode("1111"), "4:1")
    _eq(m.rle_decode("4:1"), "1111")
    _eq(m.rle_encode(":::"), "3::")
    _eq(m.rle_decode("3::"), ":::")
    _eq(m.rle_encode("aabbb111x"), "2:a3:b3:11:x")
    _eq(m.rle_decode("2:a3:b3:11:x"), "aabbb111x")
    for text in ["x", "zzzzzzzzzzzz", "a1b2c3", "  !!??##", "abcabc", "1:2:3:"]:
        _eq(m.rle_decode(m.rle_encode(text)), text)
    _raises(ValueError, m.rle_decode, "a")
    _raises(ValueError, m.rle_decode, "0:a")
    _raises(ValueError, m.rle_decode, "3")
    _raises(ValueError, m.rle_decode, "1:a2:")
    _raises(TypeError, m.rle_encode, None)
    _raises(TypeError, m.rle_encode, 123)
    _raises(TypeError, m.rle_decode, ["1:a"])


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d901_rle_codec: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
