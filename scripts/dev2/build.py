"""Build benchmarks_dev2/agent10 task directories from scripts/dev2/tasks_*.py definitions.
Usage (repo root): python scripts/dev2/build.py
Each definition: id, title, desc, symbols, invariants, stub, ref, wrong, pub, hid, reg (test bodies use m, _eq, _raises)."""
import json, textwrap, importlib, sys
from pathlib import Path

ROOT = Path("benchmarks_dev2/agent10")
TPL = '''"""{kind} for {tid} (dev2 set, written without reading any held-out test)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"{short}_{{path.stem}}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {{path}}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {{expected!r}}, got {{actual!r}}"


def _raises(error, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except error:
        return
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"expected {{error.__name__}}, got {{type(exc).__name__}}: {{exc}}")
    raise AssertionError(f"expected {{error.__name__}}")


def _checks(m):
{body}


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"{label} test failed for {tid}: {{exc}}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

def build():
    mods = [importlib.import_module(f"tasks_{n}") for n in ("a", "b")]
    n = 0
    for mod in mods:
        for t in mod.TASKS:
            d = ROOT / t["id"]
            d.mkdir(parents=True, exist_ok=True)
            spec = {"task_id": t["id"], "title": t["title"], "description": t["desc"],
                    "implementation_files": [(d / "solution_stub.py").as_posix()],
                    "symbols": t["symbols"], "invariants": t["invariants"], "max_retries": 2}
            (d / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
            (d / "solution_stub.py").write_text(t["stub"].strip("\n") + "\n")
            (d / "reference_solution.py").write_text(t["ref"].strip("\n") + "\n")
            (d / "wrong_solution.py").write_text(t["wrong"].strip("\n") + "\n")
            short = t["id"].split("_")[0]
            for fname, key, kind, label in (("public_tests.py", "pub", "Public checks", "public"),
                                            ("hidden_tests.py", "hid", "Hidden checks", "hidden"),
                                            ("regression_tests.py", "reg", "Regression checks", "regression")):
                body = textwrap.indent(textwrap.dedent(t[key]).strip("\n"), "    ")
                (d / fname).write_text(TPL.format(kind=kind, tid=t["id"], short=short, body=body, label=label))
            n += 1
    print("built", n, "tasks")

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    build()
