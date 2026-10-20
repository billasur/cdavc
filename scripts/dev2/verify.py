"""Verify dev2 tasks: reference passes public/hidden/regression; stub and wrong solution fail hidden. Run from repo root."""
import subprocess, sys
from pathlib import Path

def run(d, test, sol):
    p = subprocess.run([sys.executable, str(d / test), sol], capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stderr or p.stdout).strip()[:90]

bad = 0
print(f"{'task':34} ref(pub,hid,reg)  stub-hid  wrong-hid  wrong-pub")
for d in sorted(Path("benchmarks_dev2/agent10").glob("task_*")):
    ref = [run(d, t, "reference_solution.py")[0] for t in ("public_tests.py", "hidden_tests.py", "regression_tests.py")]
    stub = run(d, "hidden_tests.py", "solution_stub.py")[0]
    wrong = run(d, "hidden_tests.py", "wrong_solution.py")[0]
    wpub = run(d, "public_tests.py", "wrong_solution.py")[0]
    ok = ref == [0, 0, 0] and stub != 0 and wrong != 0
    bad += not ok
    print(f"{d.name:34} {ref}  {'FAIL' if stub else 'PASS?!'}      {'FAIL' if wrong else 'PASS?!'}       {'fails' if wpub else 'passes'}  {'OK' if ok else 'PROBLEM'}")
    if ref != [0, 0, 0]:
        for t in ("public_tests.py", "hidden_tests.py", "regression_tests.py"):
            c, msg = run(d, t, "reference_solution.py")
            if c: print("   ", t, msg)
print("PROBLEMS:", bad)
sys.exit(1 if bad else 0)
