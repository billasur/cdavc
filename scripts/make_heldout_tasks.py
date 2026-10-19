"""Build benchmarks_heldout/tasks.json (+ dev equivalent) for cdavc.benchmark.

Usage: python scripts/make_heldout_tasks.py benchmarks_heldout
Copies solution_stub.py to solution.py (the file a model edits) and writes a task
list in the benchmarks/tasks.json format. Run from the repo root.
"""
import json, shutil, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmarks_heldout")
tasks = []
for spec_path in sorted(root.glob("agent*/*/spec.json")):
    d = spec_path.parent
    spec = json.loads(spec_path.read_text())
    sol = d / "solution.py"
    if not sol.exists():
        shutil.copy(d / "solution_stub.py", sol)
    rel = sol.as_posix()
    # agent1 tests resolve the argument relative to the task dir; the others relative to cwd.
    # Some test files resolve their argument relative to the task dir, others relative to cwd.
    # Detect which by reading the hidden test (fix: agent7-9 dev tasks used the task-dir form too).
    task_dir_form = "parent / name" in (d / "hidden_tests.py").read_text()
    arg = "solution.py" if task_dir_form else rel
    t = dict(spec)
    t["implementation_files"] = [rel]
    t["test_files"] = [(d / n).as_posix() for n in ("public_tests.py", "hidden_tests.py", "regression_tests.py")]
    t["test_command"] = ["python", (d / "public_tests.py").as_posix(), arg]
    t["hidden_test_command"] = ["python", (d / "hidden_tests.py").as_posix(), arg]
    t["regression_command"] = ["python", (d / "regression_tests.py").as_posix(), arg]
    t.setdefault("source", "CD-AVC-night-run-original")
    tasks.append(t)
out = root / "tasks.json"
out.write_text(json.dumps({"benchmark_id": root.name, "source": "CD-AVC-night-run-original", "tasks": tasks}, indent=1))
print(f"wrote {out} with {len(tasks)} tasks")
