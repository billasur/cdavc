"""Ledger of integer cent balances with atomic operations."""


def open_account(ledger: dict, owner: str) -> None:
    raise NotImplementedError


def deposit(ledger: dict, owner: str, amount: int) -> None:
    raise NotImplementedError


def withdraw(ledger: dict, owner: str, amount: int) -> None:
    raise NotImplementedError


def transfer(ledger: dict, from_owner: str, to_owner: str, amount: int) -> None:
    raise NotImplementedError


def total(ledger: dict) -> int:
    raise NotImplementedError
