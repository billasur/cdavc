# The CD-AVC pre-merge gate

CD-AVC's core claim is that **generation and acceptance should be separate
authorities**: a model (local or frontier) proposes a patch; deterministic,
repository-specific checks decide whether it is accepted. `.github/workflows/
cdavc-gate.yml` turns that claim into a required GitHub status check, for this
repository and any other.

## What the gate does

1. Checks out the **base commit** the PR is judged against.
2. Installs the **verifier from that reviewed base** — a PR cannot weaken the
   verifier that judges it (the "generative ratification loop" escape:
   the judge must sit outside the loop it judges).
3. Replays only the PR's **implementation-file diff** (`src/cdavc/**`) through
   `cdavc verify --format diff` in a throwaway snapshot of the base tree.
4. Runs the repository's own test suite, as it exists **on the base branch**,
   against the patched tree. Test-file hashes are locked in the snapshot:
   a PR that also edits tests is still judged by the old tests, and the gate
   summary says so explicitly.
5. Writes a content-addressed evidence record (`results/verification.json`)
   and exits nonzero on rejection. Every verdict carries the exact commands,
   outputs, artifact digests and outcome class (`accepted_under_declared_checks`,
   `rejected_with_counterexample`, `inconclusive`, `environment_failure`).

The gate never calls a model, needs no API keys, and reads no secrets.

## Install it in another repository

1. Add a contract that names the files a patch may touch and the commands that
   define done (see `.github/cdavc-contract.json` in this repository):

   ```json
   {
     "implementation_files": ["src/shop/pricing.py"],
     "test_files": ["tests/test_pricing.py"],
     "symbols": [],
     "invariants": [],
     "test_command": ["python", "-m", "pytest", "-q", "tests/test_pricing.py"],
     "regression_command": ["python", "-m", "pytest", "-q"]
   }
   ```

2. Copy `.github/workflows/cdavc-gate.yml`, replace `src/cdavc/**` in the
   diff command with your implementation paths, and adjust the install step
   (any reviewed cdavc checkout or release works; installing from the PR's
   own tree would let the PR grade itself).
3. Make the job a required status check under branch protection.

Works the same for human PRs and for PRs opened by Claude Code, Codex, Cursor
or a local agent: the gate does not care who wrote the patch.

## What the gate proves — and does not

The gate proves: the patch applies cleanly under exact coordinates, leaves
every locked file (tests, config, everything outside the contract) untouched,
and passes the declared executable checks on the base tree.

It does **not** prove general correctness: `accepted_under_declared_checks`
means exactly what it says. If the declared checks are weak, acceptance is
weak. Strengthen the contract (more tests, executable property cases via
`cdavc run --property-file`, `check_repeats` for flakiness) instead of
trusting the label.

Known boundaries, by design:

- A PR adding a **new** source file must extend the contract's
  `implementation_files` list first — the allowed surface is reviewed, not
  guessed. The diff parser rejects renames, deletions and binary changes
  rather than silently dropping them.
- The gate executes the repository's own test commands; treat it like any CI
  job in a trusted-repo threat model. It is a verification workflow, not a
  sandbox for hostile code.
- Flaky suites surface as `inconclusive` (with `check_repeats > 1`), not as
  silent passes.
