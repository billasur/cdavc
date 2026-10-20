# OpenRouter free-model runs (night-run, 20 Oct 2026)

Everything here is labelled with the model that produced it and is **NOT comparable to REPORT30 (Qwen2.5-7B local)**.
Dev set only (`benchmarks_dev`). The held-out set is refused by the script unless `ALLOW_HELDOUT=1`.

## Setup (once per sandbox)
1. Python 3.12: `uv python install 3.12 && uv venv -p 3.12 ~/venv` (system python is 3.10; the repo needs 3.11+).
2. Key file: `tools vault write-file --key password --name "OpenRouter API key" --return-channel none` -> path. Never print it or commit it.
3. `git checkout night-run` (or a patch branch, one at a time), `~/venv/bin/python scripts/make_heldout_tasks.py benchmarks_dev`.

## Run one slice (model x seed x arms)
```
OPENROUTER_KEY_FILE=<path> scripts/run_openrouter.sh <model-id> <seed> [arms] [limit]
```
Writes `results/openrouter/<model>/<seed>/{records.jsonl,report.md,proxy.jsonl,meta.json}`. `meta.json` says `"data_provenance":"measured"`.
Keep identical for all slices: temperature 0, max_tokens 4096, retry cap 3, timeout 240 s, dev tasks, same task order.
`scripts/or_proxy.py` is a stdlib localhost proxy (the harness only accepts localhost). It adds the key, retries 429/5xx with Retry-After, spaces calls (`MIN_INTERVAL`, default 6 s) and limits in-flight calls (`MAX_INFLIGHT`, default 1).
`--arms` (new flag in cdavc.benchmark) runs a subset; default is all three.
Commit only your own `results/openrouter/<model>/<seed>/` path; `git pull --rebase origin night-run` before pushing.

## Rate limits (observed 20 Oct 02:5x IST)
`GET /api/v1/key` for this key: `is_free_tier: true`, `free_model_daily_requests.limit = 50` per day, shared across ALL free models. One dev run is up to 15 tasks x (1 + 4 + 4) = 135 requests, so a full dev slice does not fit in one day. Per-minute: one 429 (Retry-After 1 s) after ~10 requests in 100 s; no other limit header was returned.
Consequence: the number of parallel workers is irrelevant; the daily request cap is the limit. Two ways out (both need the user): add credit to the OpenRouter account (OpenRouter documents a higher daily free-model limit after a credit purchase; verify on the account before relying on it), or shrink the budget (`limit` tasks, fewer seeds).

## Tiers and hypotheses (all HYPOTHESES until measured)
Free models available at 02:48 IST (context in tokens, `response_format` support from the API): see `docs/OPENROUTER_MODELS.md`.
| tier | candidates (code-repair rank) | arms | patches to try |
|---|---|---|---|
| ~1-4B | liquid/lfm-2.5-2.6b:free (only one) | single, retry, cdavc | exp-1 (latest vs cumulative feedback), ast-diag |
| 7-14B | none free at this size. Nearest by active params: google/gemma-4-26b-a4b-it, xingchen-agi/xing4.0-29b-a4b, nvidia/nemotron-3-nano-omni-30b-a3b | single, retry, cdavc, baseline_fresh (exp-3) | exp-1, exp-2, patch-D, ast-diag |
| 30B+ | 1 google/gemma-4-31b-it, 2 nvidia/nemotron-3-super-120b-a12b, 3 cohere/north-mini-code (size not published in API), 4 nvidia/nemotron-3-ultra-550b-a55b | single, retry, cdavc | ast-raise-class, hidden-guidance-escalation, patch-D |
Why (hypotheses): small models fail on malformed output and misread invariants, so cdavc gates and richer failure excerpts (ast-diag, exp-1/2) may help most; large models already pass most dev tasks, so the headroom is in rare hidden-test edge cases, where hidden-guidance-escalation and ast-raise-class may matter. A ceiling effect on large models would make arms indistinguishable on 15 tasks.
- H-a constrained output: `response_format` is exposed by liquid, gemma-4 (both), xing4.0, nemotron-3-super; `structured_outputs` by liquid, xing4.0, nemotron-3-super. No GBNF. Not tested yet (daily cap); test = json_schema for the file-map, compare malformed-output rate. Hypothesis.
- H-b prompt layout (stable prefix first, volatile failure output last): not implemented or measured. Needs a patch branch; prefix-cache savings are not visible through OpenRouter free routes, so only pass rate and attempts are measurable here. Hypothesis.
- H-c per-model profile (max attempts, context, feedback verbosity cached per model): not implemented; start from tier values above. Hypothesis.
- H-d report separation: `meta.json` carries `data_provenance`; anything not in records.jsonl is "estimated" and must be labelled so. Implemented at file level only.

## Smoke (measured, not a result)
`results/openrouter/liquid_lfm-2.5-2.6b_free/1-smoke/`: liquid/lfm-2.5-2.6b:free, 2 dev tasks x 3 arms, seed 1. task_d01 passed on all 3 arms; task_d02 failed on all 3 ("ValueError during candidate execution", cause not investigated). 2 tasks is a harness check, not a pass rate.

## Groq (added 20 Oct ~03:15 IST; one key, published per-model limits)
Upstream `https://api.groq.com/openai/v1` (verified in console.groq.com/docs/openai). Limits per console.groq.com/docs/rate-limits for gpt-oss-20b, gpt-oss-120b, qwen/qwen3.8-27b: 30 RPM, 1K RPD, 8K TPM, 200K TPD (the key returned 1000 RPD / 8000 TPM headers). Models on the key: openai/gpt-oss-20b, openai/gpt-oss-120b, openai/gpt-oss-safeguard-20b, qwen/qwen3.8-27b, allam-2-7b (4096 ctx, not in the limits table), plus audio/guard models.
Run: `OPENROUTER_KEY_FILE=<groq key file> UPSTREAM=https://api.groq.com/openai/v1 TPM=8000 EXTRA='{"reasoning_effort":"low"}' PROVIDER=groq MIN_INTERVAL=1 scripts/run_openrouter.sh openai/gpt-oss-20b 1 baseline_single,baseline_retry,cdavc 8`. The proxy paces to 90% of TPM using real usage and returns a daily-cap 429 (Retry-After > 300 s) instead of retrying. Python's default User-Agent got HTTP 403 from Groq; the proxy sends its own.
Measured, openai/gpt-oss-20b (reasoning_effort low), seed 1, first 8 dev tasks (d01-d05, d801-d803), NOT comparable to REPORT30 (Qwen2.5-7B local), 8 tasks is too few for significance:
| arm | passed | mean attempts |
|---|---|---|
| baseline_single | 5/8 | 1.0 |
| baseline_retry | 7/8 | 1.5 |
| cdavc | 8/8 | 1.25 |
Cost: 30 requests, about 42K tokens (13K in, 28K out by harness records, excluding reasoning overhead not reported) of the 200K daily budget. Records: results/groq/openai_gpt-oss-20b/1/.
H-b observation (hypothesis, not tested): the prompt begins with "Benchmark arm: <arm>" and "Deterministic seed", which differ between arms, so the shared prefix is short; moving them after the contract would lengthen the stable prefix. Cached tokens do not count toward Groq limits (per docs), so layout could also affect budget. Untested.

### Groq, 2 more models (same 8 dev tasks d01-d05,d801-d803, seed 1, same settings; NOT comparable to REPORT30 (Qwen2.5-7B local))
| model | tasks | single | retry | cdavc | notes |
|---|---|---|---|---|---|
| openai/gpt-oss-20b | 8 | 5/8 | 7/8 | 8/8 | 30 requests, no 429 |
| openai/gpt-oss-120b | 8 | 8/8 | 8/8 | 8/8 | 24 requests, no 429, all first attempt; ceiling, arms indistinguishable |
| qwen/qwen3.8-27b (4-task PARTIAL, d01-d04, cut by user decision) | 4 | 4/4 | 4/4 | 4/4 | cdavc used 6 attempts vs 4: gates rejected some first attempts that baseline_single passed; not investigated. 14 successful requests, 31 429s |
Rate limit finding: qwen/qwen3.8-27b has an enforced OTPM (output tokens per minute) limit of 1000 (429 body: "Request too large ... OTPM: Limit 1000"), not in the published table, so it runs ~1 request/minute and 429s often even with TPM headroom. gpt-oss-120b and 20b only hit the 8K TPM pacing without any 429.
Operational note: background jobs in the agent sandbox only advance while the agent is actively running a command; do not rely on `nohup` plus waiting between turns. Poll with `sleep` inside a call.

### H-a and H-b on gpt-oss-20b (Groq, same 8 dev tasks, seed 1; NOT comparable to REPORT30)
- H-a (response_format json_object): screened out offline, not measured. 0 malformed-JSON failures in all stored records; json_object cannot fix Python syntax or semantic errors. A partial run (~8 records, ~10K tokens) was aborted and deleted.
- H-b (`--prompt-layout stable-prefix`, default unchanged): offline, shared prefix between attempt 1 and retry prompt rises from 6% to 98% of characters. Measured on 20B: single 3/8 (default layout 5/8), retry 7/8 (7/8), cdavc 8/8 (8/8). Mean attempts retry 1.5 and cdavc 1.375 (1.5 and 1.25 default). Prompts are ~380 tokens, below any cache threshold, so no cached tokens were reported (proxy log records usage). No repeat of the default layout was run, so the single-arm gap (2 tasks) cannot be separated from run-to-run noise at temp 0. Read: no pass-rate gain shown, the cache benefit is untestable on Groq at this prompt size; keep as opt-in.

## Zero-token checks (20 Oct ~05:07 IST, no API calls)
- `unittest discover`: all pass except `test_launch.test_main_detects_memory_when_not_explicitly_configured` (needs a real llama-server executable; environment, not caused by night-run changes).
- `benchmark --mock` on benchmarks/tasks.json (30 tasks x 3 arms): 30/30 on every arm (scripted responses, proves the harness only, not model quality). Mean wall per task: single 0.099 s, retry 0.098 s, cdavc 0.358 s, so the cage gates (locked hashes, AST contract, targeted, hidden, regression, in git worktree) cost about 0.26 s per task. Per-gate timings are not recorded (records only list gate names), so a per-gate breakdown is not available without a harness change.
- Real-run wall times in the Groq records include the proxy's TPM pacing waits, so they are not usable as gate or model latency. Mean upstream API latency: 1.3 s (20B), 1.8 s (120B), from proxy logs.
- The sandbox was rebuilt once during the night; everything is on night-run, local state is disposable.

## exp-4 hand-mutant kill rate (offline, no tokens; run from branch night-run-exp-4, 20 Oct ~09:10 IST)
`python -m cdavc.mutants --root benchmarks_heldout --max-mutants 12`: OVERALL 232/272 mutants killed = 85.3% (Wilson 95% CI 80.6-89.0%). Measured on the held-out hidden tests with the reference solutions; no model involved. Weakest: task_h404_is_bipartite 3/12, task_h34_isqrt 8/12, task_h6_03_circuit_breaker 8/12, task_h33_crt, h09_free_slots, h403_topological_order 9/12. 6 tasks were SKIPPED (h01-h05 agent1, h401): the tool says "reference does not pass hidden tests"; likely the same cwd/task-dir argument-path issue the adapter had (not verified), so those 6 tasks have no kill-rate. Mutants are capped at 12 per task by stride subsample; the uncapped run did not finish in 115 s. Some timeouts count as kills by the tool's rule. Surviving mutants may be equivalent mutants (not checked). Files: results/exp4/.

## exp-3 baseline_fresh and exp-4 fix (20 Oct ~09:17 IST)
- exp-3 merged into night-run (clean merge; adds arm baseline_fresh, independent sample per attempt, same prompt each attempt). Unit tests: 16 pass.
- Measured: openai/gpt-oss-20b (Groq), 8 dev tasks, seed 1, baseline_fresh only: 8/8 passed, 11 attempts total, 11 requests, no 429s. Compare (same model, same tasks, seed 1, default layout): baseline_single 5/8, baseline_retry 7/8 (12 attempts), cdavc 8/8 (10 attempts). CONFOUND: those used temperature 0; baseline_fresh was run at temperature 0.7 because at temperature 0 fresh samples are near-identical to the first one (stored 20B calls with the same prompt returned identical token counts), which would make the control degenerate. So the arm comparison mixes temperature and feedback; one seed, 8 tasks: no conclusion on retry-feedback vs resampling. Not comparable to REPORT30 (Qwen2.5-7B local). Records: results/groq/openai_gpt-oss-20b/1-exp3-fresh-t0.7/.
- exp-4 skipped-task fix: mutants.py passed relative paths to hidden_tests.py, which agent1 tests join to their own directory (doubled path). Fixed by resolving both paths. Re-run of the 6 skipped tasks (cap 12 mutants): h01 11/12, h02 11/12, h03 12/12, h04 9/12, h05 10/12, h401 7/7 = 60/67 killed. Combined with the earlier 232/272: 292/339 = 86.1% (Wilson 95% CI 82.1-89.4%). exp-4 is merged into night-run. File: results/exp4/heldout-mutant-rerun-6-skipped.json.

## Weak-model slice: allam-2-7b (Groq, 20 Oct ~09:30 IST; temperature 0, max_tokens 2000, seed 1, first 8 dev tasks, NOT comparable to REPORT30 (Qwen2.5-7B local))
Limits seen in headers: 7000 RPD, 6000 TPM, context 4096. Result (PARTIAL, 23 of 24 records; cdavc on d803 not run, stopped at the ~50K-token budget, used about 54.7K by proxy usage): baseline_single 0/8, baseline_retry 1/8 (23 attempts), cdavc 0/7 (21 attempts). 4 429s retried by the proxy. Failure text of the final attempts: "provider response is not a JSON files object" in 12 of 23 records, i.e. this model often does not return the required JSON; the rest were hidden-test failures (name errors, syntax errors, wrong types). So on this model malformed output is the main failure, which makes H-a (response_format / structured output) relevant here, unlike on gpt-oss. H-a was not run (token budget); allam-2-7b may not accept response_format (not checked). Records: results/groq/allam-2-7b/1-t0/.

### H-a on allam-2-7b (measured, single arm, 8 dev tasks, seed 1, temperature 0; NOT comparable to REPORT30 (Qwen2.5-7B local))
response_format json_object accepted by the API. Result 0/8 passed (default layout without it: 0/8). Of 8 requests, 4 returned HTTP 200 (all valid JSON but the generated code failed hidden tests, e.g. "invalid syntax line 1") and 4 returned HTTP 400 (Groq rejects output that is not valid JSON; the harness records these as "provider unavailable"; the 400 body text was not logged, so the reason is inferred). Without response_format the same arm had 5 non-JSON-object responses and 3 hidden-test failures. Net: the constraint turned non-JSON output into API errors rather than passes; no gain in pass rate. About 2.7K tokens. Records: results/groq/allam-2-7b/1-h-a-json/.

Result: baseline_retry at temperature 0.7: 8/8, 9 attempts (9 requests, no 429). Compare at temperature 0.7: baseline_fresh 8/8, 11 attempts. At temperature 0 (default layout): single 5/8, retry 7/8 (12 attempts), cdavc 8/8 (10 attempts). With both at 0.7 the two arms are tied on pass rate, and retry used 2 fewer attempts than fresh (one seed, 8 tasks, no significance). Temperature 0.7 itself raised retry from 7/8 to 8/8 and cut attempts from 12 to 9, so temperature (or run-to-run variance) matters as much as the arm differences seen at temperature 0. Records: results/groq/openai_gpt-oss-20b/1-retry-t0.7/.
