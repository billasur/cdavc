"""Render and validate the dev corpus from ``tools/dev_specs.py``.

The dev corpus is the only place iteration is allowed, so it is emitted as
plain files and pinned by ``benchmarks/dev/MANIFEST.sha256`` exactly like the
held-out corpus.  Expected values are derived from each task's reference
implementation; the builder refuses to emit anything if a reference disagrees
with its own cases, if a reference fails its property checks, or if the
unsolved stub already passes the public tests.

Run: ``python tools/build_dev_corpus.py``
"""

from __future__ import annotations

import hashlib
import json
import pprint
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "benchmarks" / "dev"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from dev_specs import SPECS  # noqa: E402

STUB = '''"""{title}."""


def {symbol}(*args, **kwargs):
    raise NotImplementedError
'''

HARNESS = '''"""Shared loader and assertion helper for the dev corpus tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_solution(task_id: str):
    path = ROOT / "benchmarks" / "dev" / "tasks" / task_id / "solution.py"
    spec = importlib.util.spec_from_file_location("cdavc_dev_" + task_id, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    if actual != expected or type(actual) is not type(expected):
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def run(cases, symbols, task_id: str) -> None:
    module = load_solution(task_id)
    function = getattr(module, symbols[task_id])
    for args, expected, raises in cases[task_id]:
        if raises:
            try:
                function(*args)
            except Exception as exc:  # noqa: BLE001 - the test asserts the type
                if type(exc).__name__ != raises:
                    raise AssertionError(
                        f"expected {raises}, got {type(exc).__name__}: {exc}"
                    ) from exc
            else:
                raise AssertionError(f"expected {raises}, no exception raised")
        else:
            _eq(function(*args), expected)
'''

MODULE_HEADER = '''"""{doc}"""

from __future__ import annotations

import sys

from dev_harness import run

'''


def _load_reference(source: str):
    namespace: dict[str, object] = {}
    exec(compile(source, "<reference>", "exec"), namespace)  # noqa: S102 - trusted authoring data
    return namespace


def _expected(namespace, symbol: str, args: tuple, raises: str | None):
    function = namespace[symbol]
    if raises:
        try:
            function(*args)
        except Exception as exc:  # noqa: BLE001 - authoring check
            if type(exc).__name__ != raises:
                raise SystemExit(
                    f"{symbol}{args}: reference raised {type(exc).__name__}, expected {raises}"
                )
            return None
        raise SystemExit(f"{symbol}{args}: reference did not raise {raises}")
    try:
        return function(*args)
    except Exception as exc:  # noqa: BLE001 - authoring check
        raise SystemExit(f"{symbol}{args}: reference raised {type(exc).__name__}: {exc}") from exc


def _rows(spec, key: str, namespace) -> list[tuple]:
    return [
        (args, _expected(namespace, spec["symbol"], args, raises), raises)
        for args, raises in spec[key]
    ]


def _module(doc: str, cases, symbols) -> str:
    body = pprint.pformat(cases, width=100, sort_dicts=False)
    symbol_text = pprint.pformat(symbols, width=100, sort_dicts=False)
    return (
        MODULE_HEADER.format(doc=doc)
        + f"CASES = {body}\n\nSYMBOLS = {symbol_text}\n\n"
        + 'if __name__ == "__main__":\n    run(CASES, SYMBOLS, sys.argv[1])\n'
    )


def _write_corpus() -> dict[str, dict[str, list[tuple]]]:
    namespaces = {}
    for spec in SPECS:
        namespace = _load_reference(spec["ref"])
        if not callable(namespace.get(spec["symbol"])):
            raise SystemExit(f"{spec['tid']}: reference does not define {spec['symbol']}")
        namespaces[spec["tid"]] = namespace

    public = {spec["tid"]: _rows(spec, "public", namespaces[spec["tid"]]) for spec in SPECS}
    hidden = {spec["tid"]: _rows(spec, "hidden", namespaces[spec["tid"]]) for spec in SPECS}
    regression = {
        spec["tid"]: _rows(spec, "regression", namespaces[spec["tid"]]) for spec in SPECS
    }
    symbols = {spec["tid"]: spec["symbol"] for spec in SPECS}

    if DEV.exists():
        shutil.rmtree(DEV)
    (DEV / "tasks").mkdir(parents=True)
    (DEV / "references").mkdir()

    tasks = []
    properties = {}
    for spec in SPECS:
        tid = spec["tid"]
        implementation = f"benchmarks/dev/tasks/{tid}/solution.py"
        (DEV / "tasks" / tid).mkdir()
        (DEV / "tasks" / tid / "solution.py").write_text(
            STUB.format(title=spec["description"], symbol=spec["symbol"]), encoding="utf-8"
        )
        (DEV / "references" / f"{tid}.py").write_text(spec["ref"], encoding="utf-8")
        tasks.append(
            {
                "task_id": tid,
                "title": spec["symbol"].replace("_", " "),
                "description": spec["description"],
                "source": "CD-AVC-dev-v1",
                "implementation_files": [implementation],
                "test_files": [
                    "benchmarks/dev/public_tests.py",
                    "benchmarks/dev/hidden_tests.py",
                    "benchmarks/dev/regression_tests.py",
                ],
                "symbols": [spec["symbol"]],
                "invariants": spec["invariants"],
                "test_command": ["python", "benchmarks/dev/public_tests.py", tid],
                "hidden_test_command": ["python", "benchmarks/dev/hidden_tests.py", tid],
                "regression_command": ["python", "benchmarks/dev/regression_tests.py", tid],
                "max_retries": 2,
            }
        )
        properties[tid] = [
            {
                "property": "dev_reference_matches",
                "symbol": spec["symbol"],
                "reference": f"benchmarks/dev/references/{tid}.py",
                "shape": spec["shape"],
                "cases": 12,
                "pure": bool(spec["pure"]),
            }
        ]

    (DEV / "tasks.json").write_text(
        json.dumps({"tasks": tasks}, indent=2) + "\n", encoding="utf-8"
    )
    (DEV / "properties.json").write_text(
        json.dumps({"tasks": properties}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (DEV / "dev_harness.py").write_text(HARNESS, encoding="utf-8")
    (DEV / "public_tests.py").write_text(
        _module("Public smoke checks for the dev corpus.", public, symbols), encoding="utf-8"
    )
    (DEV / "hidden_tests.py").write_text(
        _module("Hidden checks for the dev corpus. Never shown to a model.", hidden, symbols),
        encoding="utf-8",
    )
    (DEV / "regression_tests.py").write_text(
        _module("Independent regression checks for the dev corpus.", regression, symbols),
        encoding="utf-8",
    )
    return {"public": public, "hidden": hidden, "regression": regression}


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def _validate() -> None:
    from cdavc import properties as property_gate

    failures: list[str] = []
    for spec in SPECS:
        tid = spec["tid"]
        stub = (DEV / "tasks" / tid / "solution.py").read_text()
        solved = DEV / "tasks" / tid / "solution.py"
        reference = DEV / "references" / f"{tid}.py"
        try:
            shutil.copyfile(reference, solved)
            for module in ("public_tests.py", "hidden_tests.py", "regression_tests.py"):
                result = _run([sys.executable, f"benchmarks/dev/{module}", tid])
                if result.returncode != 0:
                    failures.append(f"{tid} {module}: {result.stderr.strip()[-300:]}")
            probe = property_gate.probe(
                table_path=DEV / "properties.json",
                task_id=tid,
                files=[reference],
                seed=7,
            )
            if not probe.get("ok"):
                failures.append(f"{tid} property: {probe.get('failures')}")
        finally:
            solved.write_text(stub)
        stub_run = _run([sys.executable, "benchmarks/dev/public_tests.py", tid])
        if stub_run.returncode == 0:
            failures.append(f"{tid} stub unexpectedly passes the public tests")
    if failures:
        raise SystemExit("dev corpus validation failed:\n" + "\n".join(failures))


def _manifest() -> None:
    entries = []
    for pattern in ("tasks/*/solution.py", "references/*.py"):
        entries.extend(sorted(DEV.glob(pattern)))
    for name in (
        "tasks.json",
        "properties.json",
        "public_tests.py",
        "hidden_tests.py",
        "regression_tests.py",
        "dev_harness.py",
    ):
        entries.append(DEV / name)
    lines = []
    for path in sorted(set(entries)):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (DEV / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    _write_corpus()
    _validate()
    _manifest()
    print(f"dev corpus written: {len(SPECS)} tasks, {len(list(DEV.rglob('*.py')))} python files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
