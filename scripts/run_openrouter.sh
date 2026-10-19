#!/usr/bin/env bash
# Groq: UPSTREAM=https://api.groq.com/openai/v1 TPM=8000 EXTRA='{"reasoning_effort":"low"}' PROVIDER=groq OPENROUTER_KEY_FILE=<groq key file> ...
# One slice = model x seed x arms. Usage:
#   OPENROUTER_KEY_FILE=~/.vault/.../password scripts/run_openrouter.sh <model> <seed> [arms] [limit]
# arms: comma list of baseline_single,baseline_retry,cdavc (default all). Same settings for every slice:
# temperature 0, max_tokens 4096, retry cap 3, timeout 240s, dev set only.
set -euo pipefail
MODEL=${1:?model id, e.g. liquid/lfm-2.5-2.6b:free}; SEED=${2:?seed}; ARMS=${3:-baseline_single,baseline_retry,cdavc}; LIMIT=${4:-}
KEY=${OPENROUTER_KEY_FILE:?path to file holding the key (tools vault write-file)}
PY=${PYTHON:-$HOME/venv/bin/python}
TASKS=${TASKS:-benchmarks_dev/tasks.json}
case "$TASKS" in *heldout*) [ "${ALLOW_HELDOUT:-}" = 1 ] || { echo "held-out set refused (set ALLOW_HELDOUT=1 only with user approval)"; exit 2;}; esac
cd "$(git rev-parse --show-toplevel)"
[ "$(git rev-parse --abbrev-ref HEAD)" != main ] || { echo "refusing to run on main"; exit 2; }
SLUG=$(echo "$MODEL" | tr '/:' '__'); OUT=results/${PROVIDER:-openrouter}/$SLUG/$SEED${TAG:+-$TAG}; mkdir -p "$OUT"
PORT=$(( 20000 + RANDOM % 20000 ))
"$PY" scripts/or_proxy.py --key-file "$KEY" --port "$PORT" --log "$OUT/proxy.jsonl" \
  --upstream "${UPSTREAM:-https://openrouter.ai/api/v1}" --tpm "${TPM:-0}" --extra "${EXTRA:-{\}}" --max-inflight "${MAX_INFLIGHT:-1}" --min-interval "${MIN_INTERVAL:-6}" >/dev/null 2>&1 &
PROXY=$!; trap 'kill $PROXY 2>/dev/null' EXIT; sleep 1
[ -f "$TASKS" ] || "$PY" scripts/make_heldout_tasks.py "$(dirname "$TASKS")"
PYTHONPATH=src "$PY" -m cdavc.benchmark . --tasks "$TASKS" --endpoint "http://127.0.0.1:$PORT/v1/chat/completions" \
  --model "$MODEL" --seed "$SEED" --arms "$ARMS" --timeout 240 --retry-cap 3 ${PROMPT_LAYOUT:+--prompt-layout $PROMPT_LAYOUT} ${LIMIT:+--limit $LIMIT} \
  --records "$OUT/records.jsonl" --report "$OUT/report.md" || true
cat > "$OUT/meta.json" <<JSON
{"data_provenance":"measured","model":"$MODEL","seed":$SEED,"arms":"$ARMS","tasks":"$TASKS","branch":"$(git rev-parse --abbrev-ref HEAD)","commit":"$(git rev-parse --short HEAD)",
 "provider":"${PROVIDER:-openrouter}","extra":${EXTRA:-{\}},"tpm":${TPM:-0},"prompt_layout":"${PROMPT_LAYOUT:-default}","label":"$MODEL via ${PROVIDER:-openrouter}; NOT comparable to REPORT30 (Qwen2.5-7B local)"}
JSON
echo "done: $OUT"
