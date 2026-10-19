"""Deterministic mutation testing for the CD-AVC property gate.

A property suite is only as wide as the faults it can detect.  Counting tasks
says how much *behaviour* a verifier is asked about; the mutant kill rate says
how much of that behaviour it actually checks.  This module rewrites a
candidate with small, deterministic faults and reports how many of them the
frozen property table rejects.

Every mutant is produced by one AST rewrite and re-rendered with
``ast.unparse``, so a mutant is always syntactically valid Python.  Selection
is seeded and stable for a given ``(source, seed, limit)`` pair, which is what
makes the metric comparable between runs.

    python -m cdavc.mutants --file benchmarks/mock_solutions/task_006/solution.py --mutants 4
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import sys
from collections.abc import Iterable, Mapping, Sequence
from types import ModuleType
from typing import Any

MUTANT_VERSION = "1"
DEFAULT_MUTANTS = 3
"""Mutants generated per file when the caller does not choose a count."""

OPERATORS = (
    "compare_boundary",
    "int_off_by_one",
    "negate_condition",
    "drop_branch",
    "swap_add_sub",
    "drop_return_value",
)
"""The rewrite kinds a mutant may use; the name is recorded with each mutant."""


def _apply(source: str, operator: str, key: tuple[int, int]) -> str | None:
    """Return ``source`` with one node rewritten, or ``None`` if the site is gone."""

    tree = ast.parse(source)
    selected: ast.AST | None = None
    for node in ast.walk(tree):
        if (getattr(node, "lineno", 0), getattr(node, "col_offset", 0)) == key:
            selected = node
            break
    if selected is None:
        return None
    if operator == "compare_boundary" and isinstance(selected, ast.Compare):
        flip = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt}
        if not selected.ops or type(selected.ops[0]) not in flip:
            return None
        selected.ops[0] = flip[type(selected.ops[0])]()
    elif operator == "int_off_by_one" and isinstance(selected, ast.Constant):
        if isinstance(selected.value, bool) or not isinstance(selected.value, int):
            return None
        selected.value = selected.value + 1
    elif operator == "negate_condition" and isinstance(selected, (ast.If, ast.While)):
        selected.test = ast.UnaryOp(op=ast.Not(), operand=selected.test)
    elif operator == "drop_branch" and isinstance(selected, ast.If):
        selected.body = [ast.Pass()]
    elif operator == "swap_add_sub" and isinstance(selected, ast.BinOp):
        swap = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add}
        if type(selected.op) not in swap:
            return None
        selected.op = swap[type(selected.op)]()
    elif operator == "drop_return_value" and isinstance(selected, ast.Return):
        selected.value = ast.Constant(value=None)
    else:
        return None
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree)
    except Exception:  # pragma: no cover - defensive: unparse failures are not mutants
        return None


def mutation_sites(source: str) -> list[tuple[str, tuple[int, int]]]:
    """Every deterministic rewrite site in ``source``, in a stable order."""

    tree = ast.parse(source)
    sites: list[tuple[str, tuple[int, int]]] = []
    for node in ast.walk(tree):
        key = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
        if isinstance(node, ast.Compare) and node.ops and isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            sites.append(("compare_boundary", key))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            sites.append(("int_off_by_one", key))
        elif isinstance(node, (ast.If, ast.While)):
            sites.append(("negate_condition", key))
        elif isinstance(node, ast.If):
            sites.append(("drop_branch", key))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            sites.append(("swap_add_sub", key))
        elif isinstance(node, ast.Return) and node.value is not None:
            sites.append(("drop_return_value", key))
    sites.sort(key=lambda item: (item[1], OPERATORS.index(item[0])))
    return sites


def generate_mutants(source: str, *, limit: int = DEFAULT_MUTANTS, seed: int = 0) -> list[dict[str, Any]]:
    """Return up to ``limit`` distinct mutants of ``source``, seeded and sorted."""

    if limit <= 0:
        return []
    sites = mutation_sites(source)
    if not sites:
        return []
    order = list(range(len(sites)))
    random.Random(f"{seed}:{limit}:mutants").shuffle(order)
    mutants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index in order:
        operator, key = sites[index]
        mutated = _apply(source, operator, key)
        if mutated is None or mutated == source or mutated in seen:
            continue
        seen.add(mutated)
        mutants.append({"operator": operator, "line": key[0], "column": key[1], "source": mutated})
        if len(mutants) >= limit:
            break
    return mutants


def module_from_source(source: str, *, name: str = "cdavc_mutant", attributes: Iterable[str] = ()) -> ModuleType:
    """Compile one candidate source into a fresh module namespace."""

    module = ModuleType(name)
    exec(compile(source, f"<{name}>", "exec"), module.__dict__)  # noqa: S102 - offline harness
    for attribute in attributes:
        if hasattr(module, attribute):
            setattr(module, attribute, getattr(module, attribute))
    return module


def kill_rate(
    sources: Sequence[str],
    entries: Sequence[Mapping[str, Any]],
    *,
    run_table: Any,
    seed: int = 0,
    limit: int = DEFAULT_MUTANTS,
) -> dict[str, Any]:
    """Generate mutants of ``sources`` and count how many the properties reject.

    ``run_table`` is :func:`cdavc.properties.run_table`; it is injected so the
    mutation metric always uses exactly the gate the benchmark used.
    """

    generated = 0
    killed = 0
    survivors: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        try:
            mutants = generate_mutants(source, limit=limit, seed=seed + index)
        except SyntaxError:
            continue
        for mutant in mutants:
            generated += 1
            try:
                module = module_from_source(mutant["source"], name=f"cdavc_mutant_{generated}")
                result = run_table(module, entries, seed=seed)
            except Exception:  # a mutant that cannot even import is killed
                killed += 1
                continue
            if result["ok"]:
                survivors.append({"operator": mutant["operator"], "line": mutant["line"]})
            else:
                killed += 1
    return {
        "generated": generated,
        "killed": killed,
        "survived": survivors,
        "kill_rate": (killed / generated) if generated else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic mutants of a candidate file")
    parser.add_argument("--file", type=argparse.FileType("r"), required=True)
    parser.add_argument("--mutants", type=int, default=DEFAULT_MUTANTS)
    parser.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        mutants = generate_mutants(arguments.file.read(), limit=arguments.mutants, seed=arguments.seed)
    except (OSError, SyntaxError) as exc:
        print(f"cdavc mutants: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"generated": len(mutants), "mutants": mutants}, sort_keys=True))
    return 0


__all__ = [
    "MUTANT_VERSION",
    "OPERATORS",
    "generate_mutants",
    "kill_rate",
    "main",
    "module_from_source",
    "mutation_sites",
]


if __name__ == "__main__":
    raise SystemExit(main())
