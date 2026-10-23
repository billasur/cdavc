# Offline exported-artifact example

This project starts with an intentionally incomplete implementation. Both
`candidate.json` and `candidate.diff` contain the same correct candidate for
`contract.json`. The verifier tests fresh copies and does not publish the patch.

Run from the repository root:

```bash
PYTHONPATH=src python3 -m cdavc verify \
  --directory examples/external --contract examples/external/contract.json \
  --candidate examples/external/candidate.diff --format diff --source codex \
  --output results/external-verify-demo.json

PYTHONPATH=src python3 -m cdavc compare \
  --manifest examples/external/comparison.json \
  --output results/external-comparison-demo.json
```

**No Claude, Codex or local model is called.** Those are source labels used to
demonstrate identical verification. `usage-synthetic.json` contains explicitly
synthetic counters, not real vendor telemetry. The generated comparison is a
plumbing demonstration, not model-performance or token-efficiency evidence.

For real work, replace candidates and per-call telemetry with actual exports.
Without complete upstream usage, comparison remains inconclusive rather than
claiming matched costs. See `docs/VERIFICATION_ROADMAP.md` in the repository.
