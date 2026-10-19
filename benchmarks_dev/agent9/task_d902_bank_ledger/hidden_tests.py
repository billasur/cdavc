"""Held-out checks for task_d902_bank_ledger. Do not show to a model prompt."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_d902_{path.stem}", path)
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
    ledger = {}
    m.open_account(ledger, "a")
    m.open_account(ledger, "b")
    m.deposit(ledger, "a", 50)
    before = dict(ledger)
    _raises(ValueError, m.withdraw, ledger, "a", 51)
    _eq(ledger, before)
    _raises(ValueError, m.transfer, ledger, "a", "b", 51)
    _eq(ledger, before)
    _raises(ValueError, m.transfer, ledger, "a", "a", 10)
    _eq(ledger, before)
    _raises(KeyError, m.transfer, ledger, "a", "ghost", 10)
    _eq(ledger, before)
    assert "ghost" not in ledger
    _raises(KeyError, m.deposit, ledger, "ghost", 10)
    assert "ghost" not in ledger
    m.transfer(ledger, "a", "b", 20)
    _eq(ledger, {"a": 30, "b": 20})
    _eq(m.total(ledger), 50)
    _eq(m.total({}), 0)
    _raises(ValueError, m.open_account, ledger, "a")
    _raises(ValueError, m.deposit, ledger, "a", 0)
    _raises(ValueError, m.deposit, ledger, "a", -5)
    _eq(ledger, {"a": 30, "b": 20})
    _raises(TypeError, m.deposit, ledger, "a", True)
    _raises(TypeError, m.deposit, ledger, "a", 10.0)
    _raises(TypeError, m.deposit, ledger, "a", "10")
    _raises(TypeError, m.open_account, ledger, 7)
    _raises(ValueError, m.open_account, ledger, "")
    _raises(ValueError, m.open_account, ledger, "   ")
    _raises(KeyError, m.withdraw, ledger, "nobody", 1)
    fresh = {}
    m.open_account(fresh, "x")
    _eq(fresh["x"], 0)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_d902_bank_ledger: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
