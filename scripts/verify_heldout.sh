#!/bin/sh
# Verifies the frozen held-out set: SHA-256 manifest, references pass, stubs fail hidden.
set -u
cd "$(dirname "$0")/.."
sha256sum -c benchmarks_heldout/MANIFEST.sha256 --quiet && echo "manifest OK" || { echo "MANIFEST MISMATCH"; exit 1; }
ok=0; n=0
for d in $(find benchmarks_heldout -name spec.json -exec dirname {} \; | sort); do
  D=$(cd "$d" && pwd); n=$((n+1)); r=1
  for t in public hidden regression; do python3 "$d/${t}_tests.py" "$D/reference_solution.py" >/dev/null 2>&1 || r=0; done
  python3 "$d/hidden_tests.py" "$D/solution_stub.py" >/dev/null 2>&1 && r=0
  [ $r = 1 ] && ok=$((ok+1)) || echo "BAD $d"
done
echo "$ok/$n held-out tasks valid"
