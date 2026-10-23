"""Explicit runtime contract checks, isolated per process (not a Python sandbox)."""

from __future__ import annotations

import builtins
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import keyword
import math
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any


class PropertyError(ValueError):
    """A declarative property is malformed or references an unsafe path."""


def _json_value(value: Any) -> bool:
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item) for key, item in value.items())
    return False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, init=False)
class PropertyCase:
    """Immutable JSON-backed case; create with :meth:`from_dict`.

    Required: name, file, symbol. args and kwargs default to [] and {}.
    Exactly one of expected (any finite JSON value) or raises (built-in
    exception name) is required. unchanged_args defaults to False.
    Mutable JSON values exposed by to_dict are independent copies.
    """

    name: str
    file: str
    symbol: str
    _json: str

    @classmethod
    def from_dict(cls, mapping: Mapping[str, Any]) -> PropertyCase:
        if not isinstance(mapping, Mapping):
            raise PropertyError("property must be an object")
        raw = dict(mapping)
        allowed = {"name", "file", "symbol", "args", "kwargs", "expected", "raises", "unchanged_args"}
        if set(raw) - allowed:
            raise PropertyError("unknown property fields")
        for field in ("name", "file", "symbol"):
            if type(raw.get(field)) is not str or not raw[field].strip():
                raise PropertyError(f"{field} must be a non-empty string")
        if len(raw["name"]) > 200:
            raise PropertyError("name exceeds 200 characters")
        file = raw["file"]
        path = PurePosixPath(file)
        if (path.is_absolute() or ".." in path.parts or path.suffix != ".py"
                or "\\" in file or "\x00" in file or path.as_posix() != file):
            raise PropertyError("file must be a canonical repository-relative .py path")
        if not all(part.isidentifier() and not keyword.iskeyword(part) for part in raw["symbol"].split(".")):
            raise PropertyError("symbol must be a qualified callable identifier")
        if ("expected" in raw) == ("raises" in raw):
            raise PropertyError("exactly one of expected or raises is required")
        if "raises" in raw:
            exception = getattr(builtins, raw["raises"], None) if type(raw["raises"]) is str else None
            if not isinstance(exception, type) or not issubclass(exception, BaseException):
                raise PropertyError("raises must name a built-in exception")
        raw.setdefault("args", [])
        raw.setdefault("kwargs", {})
        raw.setdefault("unchanged_args", False)
        if type(raw["args"]) is not list or type(raw["kwargs"]) is not dict:
            raise PropertyError("args must be an array and kwargs must be an object")
        if type(raw["unchanged_args"]) is not bool:
            raise PropertyError("unchanged_args must be a boolean")
        try:
            valid = _json_value(raw)
            encoded = _canonical(raw) if valid else ""
        except (RecursionError, ValueError, OverflowError) as exc:
            raise PropertyError("property must contain finite JSON values") from exc
        if not valid:
            raise PropertyError("property must contain finite JSON values")
        case = object.__new__(cls)
        for key in ("name", "file", "symbol"):
            object.__setattr__(case, key, raw[key])
        object.__setattr__(case, "_json", encoded)
        return case

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)


# Candidate output is discarded; only a small structured receipt crosses back.
# Exception messages/reprs are intentionally omitted for bounded, stable diagnostics.
_WORKER = r'''
import builtins, copy, importlib.util, json, pathlib, sys
case = json.loads(sys.argv[1])
root, target, receipt = map(pathlib.Path, sys.argv[2:5])
def finish(status, failure):
    receipt.write_text(json.dumps({"status": status, "failure": failure}))
sys.path[:0] = [str(root / "src"), str(target.parent), str(root)]
try:
    parts = [target.stem]
    parent = target.parent
    while (parent / "__init__.py").is_file():
        parts.insert(0, parent.name)
        parent = parent.parent
    sys.path.insert(0, str(parent))
    name = ".".join(parts)
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    function = module
    for part in case["symbol"].split("."):
        function = getattr(function, part)
    if not callable(function):
        raise TypeError()
except BaseException:
    finish("environment_failure", "candidate import or callable resolution failed")
else:
    args, kwargs = case["args"], case["kwargs"]
    before = copy.deepcopy((args, kwargs))
    failure = None
    try:
        result = function(*args, **kwargs)
    except BaseException as exc:
        if "raises" not in case or not isinstance(exc, getattr(builtins, case["raises"])):
            failure = "call raised an unexpected exception"
    else:
        if "raises" in case:
            failure = "expected exception was not raised"
        else:
            try:
                if not (result == case["expected"]):
                    failure = "result did not match expected value"
            except BaseException:
                failure = "result comparison failed"
    try:
        if case["unchanged_args"] and (args, kwargs) != before:
            failure = "call mutated input arguments"
    except BaseException:
        failure = "input comparison failed"
    finish("failed" if failure else "passed", failure)
'''


def evaluate_properties(root: Path, cases: Sequence[PropertyCase | Mapping], *, timeout_seconds: float = 30) -> list[dict]:
    """Run each case against the actual source in a fresh Python interpreter.

    Invalid specifications/escaping symlinks raise PropertyError before any case
    runs. Import, process-start, protocol and timeout failures are environmental.
    Digest is SHA-256 of canonical normalized case plus its bounded evidence.
    This provides process isolation, not sandboxing of arbitrary Python code.
    """
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise PropertyError("timeout_seconds must be a finite positive number")
    if not isinstance(root, Path) or not root.is_dir():
        raise PropertyError("root must be an existing directory Path")
    if not isinstance(cases, Sequence) or isinstance(cases, (str, bytes)):
        raise PropertyError("cases must be a sequence")
    root = root.resolve()
    prepared = []
    for value in cases:
        case = PropertyCase.from_dict(value.to_dict() if isinstance(value, PropertyCase) else value)
        target = (root / case.file).resolve()
        if not target.is_relative_to(root):
            raise PropertyError("property file escapes repository root")
        prepared.append((case, target))
    evidence = []
    for case, target in prepared:
        status, failure = "environment_failure", "candidate source file is unavailable"
        if target.is_file():
            with tempfile.TemporaryDirectory(prefix="cdavc-property-") as directory:
                receipt = Path(directory) / "result.json"
                env = os.environ.copy()
                env["PYTHONPATH"] = os.pathsep.join(map(str, (root / "src", target.parent, root)))
                try:
                    completed = subprocess.run(
                        [sys.executable, "-B", "-c", _WORKER, case._json, str(root), str(target), str(receipt)],
                        cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=timeout_seconds, check=False,
                    )
                    if completed.returncode != 0 or not receipt.is_file() or receipt.stat().st_size > 4096:
                        failure = "candidate process did not produce valid evidence"
                    else:
                        result = json.loads(receipt.read_text())
                        allowed_failures = {None, "candidate import or callable resolution failed",
                            "call raised an unexpected exception", "expected exception was not raised",
                            "result did not match expected value", "result comparison failed",
                            "call mutated input arguments", "input comparison failed"}
                        if (result.get("status") not in {"passed", "failed", "environment_failure"}
                                or result.get("failure") not in allowed_failures):
                            raise ValueError()
                        status, failure = result["status"], result["failure"]
                except subprocess.TimeoutExpired:
                    failure = "candidate process timed out"
                except (OSError, ValueError, TypeError, AttributeError, KeyError):
                    failure = "candidate process start or evidence read failed"
        row = dict(name=case.name, passed=status == "passed", status=status, failure=failure)
        row["digest"] = hashlib.sha256(_canonical({"case": case.to_dict(), "evidence": row}).encode()).hexdigest()
        evidence.append(row)
    return evidence
