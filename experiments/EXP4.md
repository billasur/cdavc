# Experiment 4: hand-mutant kill rate of the held-out hidden tests

Status: prepared, not measured on the full held-out set. The harness ran only as a two-task
smoke check (see Verification). Branch: night-run-exp-4 (requested name night-run/exp-4 is not a
legal git ref while branch night-run exists, so a dash is used, same as night-run-exp-3).

## Finding about the current code (night-run, before this patch)

Experiment 4 from experiments/RESEARCH.md ("Hand-mutant kill rate of hidden tests", the Meta
mutation idea) was NOT implemented. `grep -ri "mutant\|mutation" src/` finds nothing. The repo
has public/hidden/regression tests per task and arms that gate on them, but nothing that measures
whether those hidden tests can reject small, deliberate behaviour changes. A weak hidden suite
inflates every pass-rate number the cage reports (the "Are Solved Issues Really Solved Correctly?"
and EvalPlus results in RESEARCH.md section 1), and today there is no number for how strong the
held-out suites are.

## Single change

New module `src/cdavc/mutants.py` plus `tests/test_mutants.py`. Nothing else is touched: no
benchmark arm, no supervisor change, no existing file modified.

For each `benchmarks_heldout/agentN/task_*` directory it:

1. Sanity-runs `hidden_tests.py` against `reference_solution.py`; a task whose reference fails is
   reported as SKIPPED, not measured.
2. Generates single-site mutants of the reference with four hand-picked, deterministic AST
   operators: comparison swaps (`<`<->`<=`, `>`<->`>=`, `==`<->`!=`, single-operand comparisons
   only), integer constant +/- 1 (booleans excluded), negated `if`/`while` tests, and type-
   conservative arithmetic swaps (`+`<->`-`, `*`<->`//`). Mutants that fail to compile or that
   unparse to a source already seen are dropped, so no mutant is a no-op by construction.
3. Runs `python hidden_tests.py <mutant path>` in a subprocess with a timeout (default 10 s).
   Every held-out evaluator accepts an explicit solution path as argv[1] and exits 0 on pass,
   non-zero on failure; a timeout counts as killed, matching how the benchmark runner treats a
   hanging candidate.
4. Reports per-task and overall kill rate (killed / viable mutants) with a 95% Wilson score
   interval, plus the surviving mutants (operator, line, description) so a human can see exactly
   which behaviour changes the suite misses. Optional `--out report.json`.

Deterministic: same repo state always produces the same mutants and the same report. No seed, no
LLM, no network. `--max-mutants N` applies a deterministic stride subsample per task for a faster
first look.

## Hypothesis

H: the held-out hidden suites have a measurable blind spot. If the overall kill rate is clearly
below 1.0 (Wilson upper bound < 1.0 on the full set), some cage passes in results/REPORT30.md
could have survived against subtly wrong code, and the surviving-mutant list shows which tasks
need stronger hidden tests before their pass rates are trusted. Falsified if the full run kills
every mutant (overall kill rate 1.0): then the suites already reject all four operator families
at every site this harness probes.
Caveat: survivors are not automatically test gaps. Some mutants are semantically equivalent
(e.g. negating a test whose branch is unreachable for the spec's inputs); each survivor needs a
human read before the suite is called weak. Kill rate is a lower bound on suite strength, not an
exact measure.

## Verification done (this patch only; not the experiment measurement)

- `PYTHONPATH=src python3 -m unittest tests.test_mutants`: 15 tests pass, covering mutant
  determinism, no-duplicate/no-op sources, each operator family, Wilson edges and a hand-computed
  8/10 reference value, killed/survived classification on synthetic tasks, skip-on-bad-reference,
  stride subsampling, and the JSON report.
- Full suite `PYTHONPATH=src python3 -m unittest discover -s tests`: 82 tests, 1 pre-existing
  error in tests/test_launch.py (hardware memory detection; fails identically on clean night-run
  in this sandbox). Nothing else regressed.
- Smoke run on 2 real held-out tasks (task_h01_parse_config, task_h31_modinv), sandbox Python
  3.10: harness completed; h01 13/14 killed with 1 survivor, h31 18/18. These two data points are
  a harness check, not the experiment result.
- NOTE: this sandbox has Python 3.10.12 while pyproject requires >=3.11,<3.13. The module is
  3.10-compatible and all unit tests passed here, but it was not run on 3.11/3.12; the user
  should rerun the unit tests on his Mac (Homebrew Python 3.12) before trusting them.

## How to measure on the Mac (one change, 3 seeds, Wilson CI)

The kill-rate run itself is deterministic: one change (this harness), no seeds needed, Wilson CI
is printed per task and overall. On the Mac:

    cd ~/cdavc && git checkout night-run-exp-4
    PYTHONPATH=src python3 -m unittest tests.test_mutants   # expect 15 pass on 3.12
    PYTHONPATH=src python3 -m cdavc.mutants --root benchmarks_heldout \
        --timeout 10 --out results/mutation_kill_rate.json

Expected wall clock: roughly (reference check + one subprocess per mutant) x 30 tasks; the
2-task smoke took ~35 s on a container CPU, so budget 5-15 min on the M3 Air. Use
`--max-mutants 25` for a quick first pass.

Interpretation: overall kill rate and its 95% Wilson CI is the test-adequacy number. Read every
surviving mutant in the JSON; classify each as equivalent-mutant or real gap; strengthen the
hidden tests that show real gaps, then rerun - the suite diff must raise the kill rate.

Only if a downstream claim is wanted (e.g. "stronger hidden tests change REPORT30-style pass
rates"), that is a separate experiment: rerun the affected benchmark arm with 3 seeds per task
and report the pass rate per seed with Wilson CIs, labelled by model, per the REPORT30 protocol.

## Sources

- TestGen-LLM (Meta), tests accepted only if they pass, are stable, and add coverage:
  https://arxiv.org/abs/2402.09171
- Mutation-guided test generation (Meta), tests judged by whether they kill mutants:
  https://arxiv.org/abs/2501.12862
- Background on weak visible tests (RESEARCH.md section 1):
  https://arxiv.org/abs/2305.01210 , https://arxiv.org/html/2503.15223v2 ,
  https://arxiv.org/html/2511.16858v2
- ast.NodeTransformer / ast.unparse: https://docs.python.org/3/library/ast.html
- Wilson score interval: https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
