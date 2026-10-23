# Research synthesis, October 2026

Four research threads (new entrants, community sentiment, 2025–26 papers,
talks and launches) reviewed against CD-AVC's thesis: **the model proposes,
deterministic repository-specific checks decide acceptance** — for local
models first, frontier models too. Every item below links a claim to its
source and states what CD-AVC did about it. Items marked *implemented* landed
on the `research/flint-and-harness-v2` branch with tests.

## 1. The niche is heating up — and the deterministic seat is empty

- **Flint (Recursive Superintelligence, Oct 21 2026)** — open-weight Apache-2.0
  MoE coding model (39.8B total / ~2.5B active, 262K context), SWE-bench
  Verified 74.2% via **mini-swe-agent**, evaluated as pass@1 averaged over ≥5
  attempts with retrieval-assisted solves rejected. Independent reproduction
  held up (LiveCodeBench 82.2 vs claimed 80.8).
  Model card: <https://huggingface.co/RecursiveSI/flint>; launch:
  <https://recursive.com/updates/introducing-recursive-flint>; vLLM day-0:
  <https://vllm.ai/blog/2026-10-21-flint>; reproduction:
  <https://www.reddit.com/r/LocalLLaMA/comments/1xc6j8t/>. Reported failure
  modes in the wild: loop stuckness, context exhaustion, quantization-dependent
  instruction drift. The card itself says tool grammar does not prevent unsafe
  actions — **the model's own documentation prescribes a cage**.
- **Tiden (Qase, Oct 6 2026)** — "intent verification for coding agents":
  versioned specs, every promise proven by a test, branch-scoped pre-merge
  verification. Product Hunt #4 of its week. Positions the judge *outside* the
  "generative ratification loop", but specs/tests are agent-drafted and scoring
  still runs through their platform. <https://www.qase.io/blog/tiden-launch/>
- **heal.dev (Oct 22 2026)** — runtime verification in a prod-like sandbox;
  the selling point is **reproducibility** ("code review misses" what it finds).
  PH #4, 242 upvotes. <https://www.heal.dev/>
- **Continue's source-controlled AI checks (Feb 2026)** — markdown checks run
  as GitHub status checks; founder concedes LLM checks "trade breadth for
  consistency." <https://news.ycombinator.com/item?id=47049848>
- **Rosentic (Apr 2026)** / Sonar 2026 messaging — "deterministic analysis,
  same scan, same result": determinism as a marketing wedge already works.
  <https://www.producthunt.com/products/rosentic>

**Gap confirmed:** everyone converging on "generation is cheap, verification
is the bottleneck" still puts an LLM, a runtime agent, or a proprietary cloud
in the judging seat. Nobody ships a fully deterministic, repo-versioned,
model-agnostic acceptance gate that works for local models. Anthropic's own
"generator–evaluator contract" talk (<https://www.youtube.com/watch?v=mR-WAvEPREE>)
is the talk-form version of CD-AVC's architecture.

*Implemented:* `.github/workflows/cdavc-gate.yml` + `docs/PRE_MERGE_GATE.md`
— a required status check that replays a PR's implementation diff through the
deterministic verifier, with the verifier itself installed from the reviewed
base (a PR cannot weaken its own judge) and test files hash-locked to the base
branch.

## 2. Community pain, in their own words

- Agents loosening/gaming tests: "the agent kept 'fixing' tests by just
  loosening assertions until everything passed… pure chaos"; the crowd-sourced
  workaround is *hidden tests + quarantine of test edits* — exactly CD-AVC's
  locked-evaluator design. <https://www.reddit.com/r/AI_Agents/comments/1x07uw6/>
- "AI has skyrocketed production incidents" — teams under AI mandates.
  <https://www.reddit.com/r/cscareerquestions/comments/1vhhk56/>
- "Docs tell an AI coding agent what's right; only deterministic CI enforces
  it" — CD-AVC's thesis stated verbatim by a stranger.
  <https://www.reddit.com/r/LLMDevs/comments/1wgygqy/>
- Review fatigue from an AI-tool founder: "PRs piled up… standards were
  slipping." <https://news.ycombinator.com/item?id=47049848>
- Local-model users: "once it's wrong it fills my codebase with junk very
  quickly"; "the biggest quality jump usually comes from diff-only output +
  strict context slicing, not switching models… control helps more."
  <https://www.reddit.com/r/LocalLLaMA/comments/1q82ae8/>
- Benchmark-side: ImpossibleBench and the Berkeley RDI sweep document agents
  exploiting weak evaluators unprompted.
  <https://www.lesswrong.com/posts/qJYMbrabcQqCZ7iqm/impossiblebench-measuring-reward-hacking-in-llm-coding-1>,
  <https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/>

These are the quotable threads for a YC application: the pain is loud, recent,
and the manual workaround (hidden tests, quarantined edits, hand-rolled gates)
is precisely what CD-AVC productizes.

## 3. What the 2025–26 papers support

| Paper | Result | CD-AVC action |
|---|---|---|
| *S\** test-time scaling (arXiv:2502.14382) | Cluster samples by execution behavior; distinguishing input breaks ties; 3B beats GPT-4o-mini | Selection signal from execution outputs we already produce — noted as next experiment (needs a new benchmark arm) |
| *Weaver* weak-verifier ensembles (arXiv:2506.18203) | Unsupervised fusion of weak verifiers beats any single one | CD-AVC already fuses (AST, locked hashes, targeted, regression, properties); fusion weights remain future work |
| Incoherence as oracle-less error measure (arXiv:2507.00057) | Cross-sample disagreement bounds true error without gold tests | Candidate for sparse-test repos; needs multi-draw evidence, deferred |
| *UTBoost* (arXiv:2506.09289) | Augmented tests exposed 345 wrongly-passing SWE-bench patches; filter non-discriminating tests | *Implemented:* the no-op ablation — a candidate byte-identical to the original that passes the gates is rejected as non-discriminating, with the reason fed to the next draw |
| *How Many Tries Does It Take?* (arXiv:2604.10508) | Feeding errors back helps (+4.9–30pp) but assertion/logic failures repair at ~45%; gains concentrate in rounds 1–2 | *Implemented:* failure routing — syntax/name/type errors quote the rejected candidate for repair; assertion-class failures get the failure text but a fresh derivation; stagnation cap stops degenerate loops |
| *Building to the Test* (arXiv:2606.28430) | With the oracle visible, agents build to the demo while the library stays dead | CD-AVC's hidden/public split already prevents this; the no-op check adds the orthogonal audit |
| *SWE-Edit* (arXiv:2604.26102) | Edit-format choice matters; separate viewing vs editing context | CD-AVC's files/edits dual format + budgeted retrieval align; fallback between formats is future work |
| *InspectCoder* (arXiv:2510.18327) | Debugging-state feedback beats raw tracebacks (5–60% relative) | Noted: enrich failure feedback with deepest-frame locals (stdlib post-mortem); deferred |
| Agentic rubrics (arXiv:2601.04171), ESE cross-model clustering (arXiv:2603.27098), HAD (arXiv:2610.02858), FunPRM (arXiv:2601.22249) | Rubric scoring, cross-model consistency, harness-aware distillation, per-step rewards | Requires extra inference or training; logged for the roadmap, not the harness core |

Model-card engineering facts that changed the provider layer (Flint card +
vLLM post): explicit sampling parameters are part of reproducibility
(temperature 1.0 / top-p 0.95 / top-k 20), long completions need generous
output budgets, and a truncated reply is not a candidate.

*Implemented:* `SamplingParams` (temperature / top_p / top_k / max_tokens) on
`cdavc run`, the graph runner and the benchmark — sent to the server, recorded
in the ledger and in every benchmark row, and part of the experiment
fingerprint so runs with different sampling cannot silently mix. A reply cut
at the token limit is rejected with an actionable message and its
`finish_reason` is recorded in the call log.

## 4. Talks worth citing

- Simon Willison, *Engineering practices that make coding agents work* (Feb
  2026): "Tests are no longer even remotely optional" — the repo's checks are
  the spec. <https://www.youtube.com/watch?v=owmJyKVu5f8>
- Anthropic, *Build Agents That Run for Hours* (May 2026): the
  generator–evaluator contract; self-evaluation is a trap.
  <https://www.youtube.com/watch?v=mR-WAvEPRbE> (correct id in report:
  mR-WAvEPRbE / see talk page)
- Latent Space, *State of Code Evals* (Dec 2025): "unit tests as verification
  are limiting"; impossible-task canaries detect gaming.
  <https://latent.space/p/state-of-code-evals-after-swe-bench>
- Armin Ronacher, *A Year of Agents* (2026): review now happens "between me
  and my agents locally" — pre-merge gating is where the pain concentrates.
  <https://lucumr.pocoo.org/2025/12/22/a-year-of-vibes/>
- Geoffrey Huntley's /ralph loop: brute-force agents against checks — "the
  engineering that survives is verification."

## 5. What landed in the harness this pass

1. **macOS sandbox-path fix** in `_safe_target` — 52 of 53 inherited red tests
   were one symlink-resolution bug (`/var` → `/private/var`); the suite was
   green on Linux CI and red on developer Macs. Also attached missing
   verification evidence to inconclusive/environment early exits so the CLI and
   benchmark expose identical evidence objects.
2. **Sampling controls + truncation honesty** (above).
3. **Stagnation detection**: a byte-identical rejected reply stops the draw
   loop with a distinct `stagnation` outcome instead of burning the budget —
   the exact failure mode Flint users report.
4. **No-op ablation gate**: passing checks accept a byte-unchanged project ⇒
   the checks do not discriminate the task; rejected with that reason.
5. **Failure-class repair routing** (assertion vs traceable error).
6. **AST-aware context**: Python files chunk at top-level statement
   boundaries (decorators kept with definitions, oversized regions split at
   line ends, definitions rank above body mentions, equal scores pack in
   reading order as a contiguous prefix). Zero additional model calls.
7. **Pre-merge GitHub gate** (dogfooded on this repository) with the judge
   installed from the reviewed base and base-locked tests.

## 6. Next, in measured order

1. **Execution-behavior selection arm** (S\*/incoherence): draw N candidates,
   cluster by public-test output signatures, select by cluster size then
   deterministic tie-breakers — measured against first-accepted under the
   existing public-selection/held-out-once protocol before it becomes default.
2. **Verifier-fusion weighting** (Weaver): unsupervised weights over the
   existing gate family, validated on the frozen adversarial fixtures.
3. **Failure feedback enrichment** (InspectCoder): deepest-frame locals in
   repair prompts.
4. **Cross-model consistency** (ESE): when several local endpoints exist,
   disagreement across models is a cheap suspicion signal on sparse-test repos.
5. **Design-partner pilots**: the YC research is unambiguous — the next
   milestone that matters is external teams running the gate on real PRs, not
   another internal benchmark point.

*Sources for every claim are inline above; research was gathered via TinyFish
search/fetch on 2026-10-24. Community quotes are verbatim from linked threads.*
