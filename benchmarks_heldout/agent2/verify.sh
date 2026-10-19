#!/bin/sh
# Reference must pass public+hidden+regression; stub must fail hidden.
cd "$(dirname "$0")"; rc=0
for d in task_h*/; do
  d=${d%/}
  for k in public hidden regression; do
    python3 $d/${k}_tests.py $d/reference_solution.py || { echo "FAIL ref $d $k"; rc=1; }
  done
  python3 $d/hidden_tests.py $d/solution_stub.py 2>/dev/null && { echo "FAIL stub passes hidden $d"; rc=1; }
  echo "$d checked"
done
exit $rc
