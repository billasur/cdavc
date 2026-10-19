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
