"""Independent regression checks for task_d902_bank_ledger."""

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


def _checks(m):
    ledger = {}
    m.open_account(ledger, "p")
    m.open_account(ledger, "q")
    m.deposit(ledger, "p", 200)
    m.transfer(ledger, "p", "q", 75)
    _eq(m.total(ledger), 200)
    _eq(ledger, {"p": 125, "q": 75})


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - regression failures are gate data
        print(f"regression test failed for task_d902_bank_ledger: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
