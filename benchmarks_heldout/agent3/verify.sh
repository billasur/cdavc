#!/bin/sh
# reference must pass all three evaluators; stub must fail hidden.
cd "$(dirname "$0")" || exit 1
rc=0
for d in task_*; do
  for t in public hidden regression; do
    python3 $d/${t}_tests.py $d/reference_solution.py || { echo "REF FAIL $t $d"; rc=1; }
  done
  python3 $d/hidden_tests.py $d/solution_stub.py 2>/dev/null && { echo "STUB PASSES hidden $d"; rc=1; }
done
[ $rc = 0 ] && echo "ok: references pass all, stubs fail hidden"
exit $rc
