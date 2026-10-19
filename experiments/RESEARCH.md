# Research notes (night-run, 20 Oct 2026)

Status: every idea below is UNVERIFIED for CD-AVC until measured. Source facts come from the abstracts/pages fetched via web search on 20 Oct 2026; nothing here was run. Repo facts: `src/cdavc/benchmark.py` has arms `baseline_single`, `baseline_retry`, `cdavc`; attempts = `min(task.max_retries, retry_cap) + 1` (line ~325); `supervisor.py` loops `range(1, task.max_retries + 2)`. Any idea tested must be labelled "prepared, not measured" until a run exists.

## 1. Test-overfitting and stale evidence (closest to the cage)
- https://dl.acm.org/doi/pdf/10.1145/3843282.3844438 ("Looping Is Not Reliability", typed revision contracts)
  - Idea: on retry, give the model only feedback from the CURRENT candidate, never traces from an earlier candidate; keep the last verified-passing checkpoint and never replace it with a worse one.
  - Test: arm A feeds all prior failure traces, arm B feeds only the latest; same sample budget.
  - Caveat: the paper reports stale traces harmed 34/135 correct starts vs 4/135 with current traces on 14B models, HumanEval-style tasks; its own policy trial failed its joint criterion. Small-model, one benchmark.
- https://arxiv.org/html/2511.16858v2 (Investigating Test Overfitting on SWE-bench)
  - Idea: code refined against generated or visible tests can pass them and still miss cases; keep hidden/regression tests out of the loop and report public-pass vs hidden-pass gap.
  - Caveat: studied on SWE-bench issue resolution, not small stdlib functions.
- https://arxiv.org/html/2503.15223v2 (Are "Solved Issues" in SWE-bench Really Solved Correctly?)
  - Idea: weak tests accept wrong patches; supports measuring hidden-test pass rate separately from public-test pass rate.
  - Caveat: abstract-level read only.
- https://arxiv.org/abs/2305.01210 (EvalPlus)
  - Idea: base tests accept flawed solutions; add extra edge-case tests. Supports the held-out hidden-test design.
  - Caveat: HumanEval-centric.

## 2. Retry and repair strategies
- https://arxiv.org/abs/2304.05128 (Self-Debugging)
  - Idea: feed execution results plus the model's own explanation of its code back into the next attempt.
  - Test: add a "explain the failure first" line to the retry prompt only.
  - Caveat: few-shot, large models; may not help 2B-9B.
- https://arxiv.org/abs/2306.09896 (Is Self-Repair a Silver Bullet?)
  - Idea: when repair cost is counted, gains are modest and limited by the quality of the model's feedback; compare repair against simply drawing more fresh samples at equal budget.
  - Test: at equal attempt count, "retry with feedback" vs "retry with a fresh independent sample".
  - Caveat: abstract says gains are bottlenecked by feedback quality; this is the key control for baseline_retry vs cdavc.
- https://arxiv.org/abs/2303.11366 (Reflexion)
  - Idea: keep a short written reflection from failed attempts as memory for the next attempt.
  - Caveat: overlaps with Self-Debugging; trace-staleness risk from section 1 applies.
- https://arxiv.org/abs/2303.17651 (Self-Refine)
  - Idea: same-model feedback then refine loop.
  - Caveat: no execution signal; weaker than test-based feedback for code. Low priority.
- https://arxiv.org/abs/2407.21787 (Large Language Monkeys)
  - Idea: coverage rises with the number of samples; with a perfect verifier, sampling more beats one try. CD-AVC's gates are the verifier.
  - Test: vary samples per task with a fixed verifier and plot pass vs attempts.
  - Caveat: gains depend on verifier precision; imperfect verifiers cap results.

## 3. Verification and selection
- https://arxiv.org/abs/2207.10397 (CodeT)
  - Idea: rank candidates by agreement between generated tests and generated solutions.
  - Caveat: needs several candidates per task; not the current single-candidate loop.
- https://aclanthology.org/2025.acl-long.343/ (CodeRM, Dynamic Scaling of Unit Tests)
  - Idea: LLM-written unit tests are unreliable reward signals; more tests per problem improves signal.
  - Caveat: relates to model-written tests; CD-AVC tests are author-written, so applies mainly if tests are model-generated.
- https://arxiv.org/abs/2402.09171 (TestGen-LLM at Meta) and https://arxiv.org/abs/2501.12862 (Mutation-guided test generation at Meta)
  - Idea: accept a test only if it passes, is stable on reruns, and adds measurable coverage or kills a mutant.
  - Test (cheap): mutate each reference solution by hand (e.g. off-by-one) and check hidden tests catch it. Gives a test-adequacy number for the held-out set.
  - Caveat: industrial Python/Kotlin setups; stdlib-only here, so hand mutants or a small AST mutator.
- https://dlnext.acm.org/doi/10.1145/3696630.3728702 (Prompts to Properties: property-based testing for LLM code) and https://arxiv.org/html/2510.09907v1 (Agentic Property-Based Testing)
  - Idea: state invariants as properties and fuzz them with seeded random inputs to find edge cases that example tests miss. Stdlib `random` with a fixed seed keeps it deterministic.
  - Caveat: fetched only search excerpts, not full text; claims not checked.

## 4. Agent scaffolding
- https://arxiv.org/abs/2405.15793 (SWE-agent)
  - Idea: concise, structured tool feedback (linter on edit, bounded output) helps agents.
  - Test: truncate and structure failure output given to the retry prompt (first failing assertion only).
  - Caveat: tied to repo-level tasks and a custom interface.
- https://arxiv.org/abs/2407.01489 (Agentless)
  - Idea: a simple localize-repair-validate pipeline without an agent loop can match agents.
  - Caveat: repo-scale bug fixing, not function-level generation.

## Suggested single-change experiments (all "prepared, not measured")
1. Latest-trace-only retry feedback vs cumulative feedback (section 1, first source).
2. Truncated first-failure feedback vs full pytest output (SWE-agent).
3. Retry with feedback vs fresh independent sample at equal attempts (Self-Repair control).
4. Hand-mutant kill rate of hidden tests (Meta mutation idea).
Only one change per experiment; same sample budget in all arms.
