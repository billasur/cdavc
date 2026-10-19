"""Map declared task invariants onto deterministic AST checks.

A task contract may state that an implementation has to reject invalid input,
for example ``Raise ValueError for negative input``.  The cage uses
:func:`required_exception` to recognise that declaration and
:func:`raises_exception` to reject candidates that never raise the declared
exception class.
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


def _exception_name(node: ast.AST | None) -> str | None:
    """Return the class name a ``raise`` expression refers to, if resolvable.

    Handles ``raise ValueError``, ``raise ValueError(...)`` and attribute
    forms such as ``raise errors.ValueError(...)`` by their final name.
    Anything else (a bare ``raise`` re-raise, a variable, a call on a
    variable) cannot be resolved statically and returns ``None``.
    """

    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def raises_exception(tree: ast.AST, name: str) -> bool:
    """Return whether the parsed module raises the named exception class.

    The contract names the exception, so the check requires the named class
    itself; a locally defined subclass is not resolved statically.
    """

    return any(
        isinstance(node, ast.Raise) and _exception_name(node.exc) == name
        for node in ast.walk(tree)
    )
