"""One deterministic verifier for generated and externally supplied artifacts.

Fresh filesystem copies and integrity hashes are not an OS security sandbox.
Only run trusted evaluators/candidates; see SECURITY.md.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .accounting import digest
from .edits import _safe_target, apply_candidate
from .invariants import has_raise_statement, required_exception
from .properties import PropertyCase, evaluate_properties
from .redact import redact_paths


VERIFIER_VERSION = "1"
_IGNORED = {"node_modules", "__pycache__", "results", "artifacts", "execution_log.json",
            "execution_report.md", "execution_patch.diff"}
_EMPTY = re.compile(r"\bRan 0 tests\b|\bno tests ran\b", re.IGNORECASE)
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _ignored(name: str) -> bool:
    return name.startswith(".") or name in _IGNORED or name.endswith(".pyc")


@dataclass(frozen=True)
class WorkspaceSnapshot:
    files: tuple[tuple[str, bytes, int], ...]
    directories: tuple[str, ...] = ()

    @classmethod
    def capture(cls, root: Path, *, exclude_paths: Sequence[str] = ()) -> WorkspaceSnapshot:
        root = Path(root).resolve()
        if not root.is_dir():
            raise ValueError("snapshot root must be a directory")
        excluded = set(exclude_paths)
        if any(not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts for name in excluded):
            raise ValueError("snapshot exclusions must be repository-relative paths")

        def skip(path: Path) -> bool:
            relative = path.relative_to(root).as_posix()
            return _ignored(path.name) or any(relative == name or relative.startswith(name + "/") for name in excluded)

        files, directories = [], []
        for directory, names, leaves in os.walk(root, followlinks=False):
            names[:] = sorted(name for name in names if not skip(Path(directory) / name))
            for name in names:
                path = Path(directory) / name
                if path.is_symlink():
                    raise ValueError("snapshot cannot include symlink directories")
                directories.append(path.relative_to(root).as_posix())
            for name in sorted(leaves):
                if skip(Path(directory) / name):
                    continue
                path = Path(directory) / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError("snapshot requires regular files, not symlinks or devices")
                files.append((path.relative_to(root).as_posix(), path.read_bytes(), path.stat().st_mode & 0o777))
        return cls(tuple(sorted(files)), tuple(sorted(directories)))

    def manifest(self) -> dict[str, Any]:
        return {"files": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "mode": mode}
                          for name, raw, mode in self.files}, "directories": list(self.directories)}

    @property
    def digest(self) -> str:
        return digest(self.manifest())

    @contextlib.contextmanager
    def materialize(self):
        with tempfile.TemporaryDirectory(prefix="cdavc-candidate-") as directory:
            root = Path(directory)
            for name in self.directories:
                (root / name).mkdir(parents=True, exist_ok=True)
            for name, raw, mode in self.files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                path.chmod(mode)
            yield root


class ArtifactStore:
    """Create-once canonical JSON objects; reusing a corrupt object fails closed."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, payload: Any) -> str:
        key = digest(payload)
        path = self.root / f"{key}.json"
        try:
            with path.open("x") as stream:
                stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        except FileExistsError:
            self.get(key)
        return key

    def get(self, key: str) -> Any:
        if not isinstance(key, str) or re.fullmatch(r"[a-f0-9]{64}", key) is None:
            raise ValueError("invalid artifact digest")
        try:
            payload = json.loads((self.root / f"{key}.json").read_text())
        except (ValueError, OSError) as exc:
            raise ValueError("artifact digest cannot be verified") from exc
        if digest(payload) != key:
            raise ValueError("artifact digest mismatch")
        return payload


@dataclass(frozen=True)
class VerificationContract:
    implementation_files: tuple[str, ...]
    test_files: tuple[str, ...]
    symbols: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    test_command: tuple[str, ...] | None = None
    negative_test_command: tuple[str, ...] | None = None
    regression_command: tuple[str, ...] | None = None
    properties: tuple[PropertyCase, ...] = ()
    boundary_probe: bool = False
    check_repeats: int = 1

    def __post_init__(self) -> None:
        for name in ("implementation_files", "test_files"):
            values = getattr(self, name)
            if not isinstance(values, (list, tuple)) or not values or not all(isinstance(value, str) for value in values) or len(set(values)) != len(values):
                raise ValueError(f"{name} must be nonempty unique paths")
            for value in values:
                path = Path(value)
                if not isinstance(value, str) or path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
                    raise ValueError("contract paths must be canonical repository-relative paths")
            object.__setattr__(self, name, tuple(values))
        for name in ("symbols", "invariants"):
            values = getattr(self, name)
            if not isinstance(values, (list, tuple)) or not all(isinstance(value, str) and value for value in values):
                raise ValueError(f"{name} must be a sequence of nonempty strings")
            object.__setattr__(self, name, tuple(values))
        if set(self.implementation_files) & set(self.test_files):
            raise ValueError("implementation and evaluator files must be disjoint")
        if isinstance(self.check_repeats, bool) or not isinstance(self.check_repeats, int) or not 1 <= self.check_repeats <= 5:
            raise ValueError("check_repeats must be between 1 and 5")
        if not isinstance(self.boundary_probe, bool):
            raise ValueError("boundary_probe must be boolean")
        if not isinstance(self.properties, (list, tuple)):
            raise ValueError("properties must be a sequence of explicit cases")
        cases = tuple(PropertyCase.from_dict(case.to_dict() if isinstance(case, PropertyCase) else case)
                      for case in self.properties)
        if any(case.file not in self.implementation_files for case in cases):
            raise ValueError("property targets must be implementation files")
        object.__setattr__(self, "properties", cases)
        for name in ("test_command", "negative_test_command", "regression_command"):
            command = getattr(self, name)
            if command is not None and (not isinstance(command, (list, tuple)) or not command
                    or not all(isinstance(word, str) and word and "\x00" not in word for word in command)):
                raise ValueError(f"{name} must be a nonempty argv sequence")
            if command is not None:
                object.__setattr__(self, name, tuple(command))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["properties"] = [case.to_dict() for case in self.properties]
        return payload

    @classmethod
    def from_task(cls, task: Any) -> VerificationContract:
        return cls(**{name: getattr(task, name, field.default)
                      for name, field in cls.__dataclass_fields__.items()})

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VerificationContract:
        if not isinstance(payload, Mapping) or set(payload) - cls.__dataclass_fields__.keys():
            raise ValueError("unknown verification contract fields")
        if not {"implementation_files", "test_files"} <= payload.keys():
            raise ValueError("contract requires implementation_files and test_files")
        return cls(**payload)


def run_command(command: Sequence[str], root: Path, label: str, *, timeout_seconds: float = 30,
                seed: int = 0, include_output: bool = True, reject_empty_tests: bool = True) -> dict[str, Any]:
    words = list(command)
    overrides: dict[str, str] = {}
    while words and _ASSIGN.match(words[0]):
        name, _, value = words.pop(0).partition("=")
        overrides[name] = value
    receipt = {"gate": label, "command": list(command), "status": "environment_failure",
               "returncode": None, "output": "", "failure": ""}
    if not words:
        receipt["failure"] = f"{label} could not start: command only sets environment variables"
        return receipt
    if words[0] in {"python", "python3"}:
        words[0] = sys.executable
    env = dict(os.environ)
    env.update(overrides)
    # Do not inherit the harness's relative PYTHONPATH into a different project.
    env["PYTHONPATH"] = os.pathsep.join((str(root / "src"), str(root), overrides.get("PYTHONPATH", "")))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = str(seed)
    env["CDAVC_SEED"] = str(seed)
    try:
        result = subprocess.run(words, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        receipt["failure"] = f"{label} timed out"
        return receipt
    except OSError:
        receipt["failure"] = f"{label} could not start"
        return receipt
    output = redact_paths(result.stdout + "\n" + result.stderr, root, root).strip()[-4000:]
    # unittest's duration is nondeterministic; do not sign it as evidence content.
    output = re.sub(r"(Ran \d+ tests? in )\d+(?:\.\d+)?s", r"\1<TIME>s", output)
    receipt.update(returncode=result.returncode, status="passed" if result.returncode == 0 else "failed")
    receipt["output"] = output if include_output else ""
    # Emptiness outranks the exit code: newer unittest versions exit nonzero for a
    # discovery that ran nothing, but the verdict that matters is still "verified
    # nothing", on every interpreter version.
    if reject_empty_tests and _EMPTY.search(output):
        flag = "--test-command" if label == "targeted test" else "--regression"
        receipt.update(status="inconclusive", failure=f"{label} ran no tests, so it verified nothing; supply {flag}")
    elif result.returncode:
        receipt["failure"] = f"{label} failed" + (f":\n{output}" if include_output and output else "")
    return receipt


def _hashes(root: Path) -> dict[str, str]:
    return {name: values["sha256"] for name, values in WorkspaceSnapshot.capture(root).manifest()["files"].items()}


def _integrity(root: Path, locked: Mapping[str, str]) -> str:
    for name, expected in locked.items():
        try:
            path = _safe_target(root, name)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return f"immutable artifact changed: {name}"
        except (ValueError, OSError):
            return f"immutable artifact changed: {name}"
    return ""


def candidate_payload(root: Path, contract: VerificationContract) -> dict[str, Any]:
    return {"files": {name: _safe_target(root, name).read_bytes().decode("utf-8") for name in contract.implementation_files}}


def verify_workspace(root: Path, contract: VerificationContract, *, snapshot: WorkspaceSnapshot | None = None,
                     store: ArtifactStore | None = None, seed: int = 0, timeout_seconds: float = 30,
                     command_runner: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Verify an already-applied candidate; each command repetition gets a fresh copy."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("verification timeout must be finite and positive")
    root = Path(root).resolve()
    snapshot = snapshot or WorkspaceSnapshot.capture(root)
    evidence: dict[str, Any] = {
        "schema": VERIFIER_VERSION, "snapshot_digest": snapshot.digest,
        "contract_digest": digest(contract.to_dict()), "artifact_digest": None,
        "accepted": False, "outcome": "rejected_with_counterexample", "failure": "",
        "gates": [], "checks": [], "properties": [],
    }

    def finish(failure: str = "", outcome: str = "rejected_with_counterexample") -> dict[str, Any]:
        evidence.update(failure=failure, outcome=outcome, accepted=outcome == "accepted_under_declared_checks")
        key = store.put(evidence) if store else digest(evidence)
        return {**evidence, "evidence_digest": key}

    protected = {name: item["sha256"] for name, item in snapshot.manifest()["files"].items()
                 if name not in contract.implementation_files}
    failure = _integrity(root, protected)
    if failure:
        return finish(failure)
    for name in contract.test_files:
        if name not in protected or not (root / name).is_file():
            return finish(f"declared test file does not exist or is not locked: {name}")
    evidence["gates"].append("locked_test_hashes")
    try:
        artifact = candidate_payload(root, contract)
        evidence["artifact_digest"] = store.put(artifact) if store else digest(artifact)
        declared: set[str] = set()
        raises = False
        for name, source in artifact["files"].items():
            if not name.endswith(".py"):
                continue
            tree = ast.parse(source, filename=name)
            declared.update(node.name for node in ast.walk(tree)
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
            raises = raises or has_raise_statement(tree)
        missing = set(contract.symbols) - declared
        if missing:
            return finish(f"AST contract is missing a required symbol; missing symbols {sorted(missing)}")
        required = required_exception(contract.invariants)
        if required and not raises:
            return finish(f"AST Contract Failed: Task invariant requires input validation raising {required}, "
                          "but no Raise statements were found in implementation.")
    except (ValueError, OSError, SyntaxError, UnicodeError) as exc:
        return finish(f"AST contract failed: {type(exc).__name__}")
    evidence["gates"].append("ast_contract")
    candidate = WorkspaceSnapshot.capture(root)
    locked = {name: values["sha256"] for name, values in candidate.manifest()["files"].items()}

    def check(label: str, operation: Callable[[Path], dict[str, Any]], *, property_check: bool = False) -> dict[str, Any] | None:
        runs = []
        for _ in range(contract.check_repeats):
            with candidate.materialize() as workspace:
                try:
                    receipt = operation(workspace)
                except Exception as exc:
                    receipt = getattr(exc, "receipt", {"status": "failed", "failure": str(exc)})
                changed = _integrity(workspace, locked)
                if changed:
                    row = {"gate": label, "runs": runs, "integrity_failure": changed}
                    evidence["checks"].append(row)
                    if property_check:
                        evidence["properties"].append(row)
                    return finish(changed)
                runs.append(receipt)
        row = {"gate": label, "runs": runs}
        evidence["checks"].append(row)
        if property_check:
            evidence["properties"].append(row)
        statuses = {row["status"] for row in runs}
        if len(statuses) > 1:
            return finish(f"{label} is flaky: repeated verdicts disagree", "inconclusive")
        if statuses != {"passed"}:
            status = next(iter(statuses))
            outcome = status if status in {"environment_failure", "inconclusive"} else "rejected_with_counterexample"
            return finish(runs[0].get("failure") or f"{label} failed", outcome)
        return None

    def command_check(command: Sequence[str], label: str) -> dict[str, Any] | None:
        def operation(workspace: Path) -> dict[str, Any]:
            if command_runner:
                result = command_runner(command, workspace, label, include_output=True)
                return result or {"status": "passed", "failure": ""}
            return run_command(command, workspace, label, timeout_seconds=timeout_seconds, seed=seed)
        return check(label, operation)

    if contract.boundary_probe:
        # Legacy opt-in probe remains diagnostic; explicit properties are stronger.
        script = _boundary_script(contract)
        result = command_check(("python", "-c", script), "boundary probe")
        if result:
            return result
        evidence["gates"].append("boundary_probe")
    for command, label, gate in ((contract.test_command, "targeted test", "targeted_test"),
                                  (contract.negative_test_command, "negative test", "negative_test"),
                                  (contract.regression_command, "regression test", "regression")):
        if command:
            result = command_check(command, label)
            if result:
                return result
            evidence["gates"].append(gate)
    for case in contract.properties:
        def operation(workspace: Path, case: PropertyCase = case) -> dict[str, Any]:
            return evaluate_properties(workspace, [case], timeout_seconds=timeout_seconds)[0]
        result = check(f"property:{case.name}", operation, property_check=True)
        if result:
            return result
    if contract.properties:
        evidence["gates"].append("contract_properties")
    if not evidence["checks"]:
        return finish("no executable checks were declared", "inconclusive")
    return finish(outcome="accepted_under_declared_checks")


def _boundary_script(contract: VerificationContract) -> str:
    spec = json.dumps({"files": list(contract.implementation_files), "symbols": list(contract.symbols)})
    return (
        "import importlib.util, json, pathlib, sys\n"
        f"spec=json.loads({spec!r})\n"
        "for path in spec['files']:\n"
        "    sys.path.insert(0, str(pathlib.Path(path).resolve().parent))\n"
        "    loader=importlib.util.spec_from_file_location('cdavc_probe', path)\n"
        "    module=importlib.util.module_from_spec(loader); loader.loader.exec_module(module)\n"
        "    for symbol in spec['symbols']:\n"
        "        function=getattr(module,symbol,None)\n"
        "        if not callable(function): continue\n"
        "        for args in ((), ('',), ([],), (0,)):\n"
        "            try: function(*args)\n"
        "            except (IndexError, ZeroDivisionError): raise\n"
        "            except Exception: pass\n"
    )


def verify_candidate(snapshot: WorkspaceSnapshot, payload: Mapping[str, Any], contract: VerificationContract,
                     *, store: ArtifactStore | None = None, seed: int = 0,
                     timeout_seconds: float = 30) -> dict[str, Any]:
    with snapshot.materialize() as root:
        try:
            apply_candidate(root, contract.implementation_files, payload)
        except (ValueError, OSError) as exc:
            evidence = {"schema": VERIFIER_VERSION, "snapshot_digest": snapshot.digest,
                        "contract_digest": digest(contract.to_dict()), "artifact_digest": None,
                        "accepted": False, "outcome": "rejected_with_counterexample",
                        "failure": str(exc), "gates": [], "checks": [], "properties": []}
            key = store.put(evidence) if store else digest(evidence)
            return {**evidence, "evidence_digest": key}
        return verify_workspace(root, contract, snapshot=snapshot, store=store,
                                seed=seed, timeout_seconds=timeout_seconds)
