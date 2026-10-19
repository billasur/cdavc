# LOG entry: EXP4 (merge into experiments/LOG.md)

- EXP4 (patch analyst, branch night-run-exp-4): implemented the RESEARCH.md experiment-4 idea -
  hand-mutant kill rate of held-out hidden tests. New src/cdavc/mutants.py (deterministic AST
  mutator: comparison swaps, int constant +/-1, negated if/while tests, arithmetic swaps;
  subprocess per mutant against hidden_tests.py; Wilson 95% CI per task and overall; surviving
  mutants listed) plus tests/test_mutants.py (15 tests). No existing file modified. Status:
  prepared, not measured on the full set. Unit tests pass on sandbox Python 3.10 (repo wants
  3.11/3.12 - rerun on the Mac); 82-test suite shows only the pre-existing test_launch sandbox
  error. Two-task smoke: h01 13/14 killed (1 survivor), h31 18/18. Full measurement command and
  interpretation steps are in experiments/EXP4.md.
