"""Ledger of integer cent balances with atomic operations."""


def _check_owner(owner):
    if not isinstance(owner, str):
        raise TypeError("owner must be str")
    if not owner.strip():
        raise ValueError("owner must be non-empty")


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("amount must be int")
    if amount <= 0:
        raise ValueError("amount must be positive")


def open_account(ledger: dict, owner: str) -> None:
    _check_owner(owner)
    if owner in ledger:
        raise ValueError(f"account exists: {owner!r}")
    ledger[owner] = 0


def deposit(ledger: dict, owner: str, amount: int) -> None:
    _check_owner(owner)
    _check_amount(amount)
    if owner not in ledger:
        raise KeyError(owner)
    ledger[owner] += amount


def withdraw(ledger: dict, owner: str, amount: int) -> None:
    _check_owner(owner)
    _check_amount(amount)
    if owner not in ledger:
        raise KeyError(owner)
    if ledger[owner] < amount:
        raise ValueError("insufficient funds")
    ledger[owner] -= amount


def transfer(ledger: dict, from_owner: str, to_owner: str, amount: int) -> None:
    _check_owner(from_owner)
    _check_owner(to_owner)
    _check_amount(amount)
    if from_owner not in ledger:
        raise KeyError(from_owner)
    if to_owner not in ledger:
        raise KeyError(to_owner)
    if from_owner == to_owner:
        raise ValueError("cannot transfer to self")
    if ledger[from_owner] < amount:
        raise ValueError("insufficient funds")
    ledger[from_owner] -= amount
    ledger[to_owner] += amount


def total(ledger: dict) -> int:
    return sum(ledger.values())
