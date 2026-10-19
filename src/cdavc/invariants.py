"""Map declared task invariants onto deterministic AST checks.

A task contract may state that an implementation has to reject invalid input,
for example ``Raise ValueError for negative input``.  The cage uses
:func:`required_exception` to recognise that declaration and
:func:`has_raise_statement` to reject candidates that never raise at all.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable

_RAISE_INVARIANT = re.compile(r"\braise\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))", re.IGNORECASE)


def required_exception(invariants: Iterable[str]) -> str | None:
    """Return the exception an invariant says the implementation must raise.

    Only names ending in ``Error`` or ``Exception`` count, so prose such as
    "raise an error for empty input" does not demand a specific class.
    """

    for invariant in invariants:
        match = _RAISE_INVARIANT.search(invariant)
        if match:
            return match.group(1)
    return None


def has_raise_statement(tree: ast.AST) -> bool:
    """Return whether the parsed module contains at least one ``raise``."""

    return any(isinstance(node, ast.Raise) for node in ast.walk(tree))
