#!/usr/bin/env bash
# Run one judge model across both difficulty tiers of the memory-vs-J frontier.
#
# Modal-agnostic: works anywhere there is a qfire binary and a reachable Ollama
# with the model already pulled. The single-rule `judge_scope` chain isolates
# the judge so the backend model's verdict is the only deciding factor; we vary
# only QFIRE_JUDGE_MODEL. `--no-cache` is required (the verdict cache key omits
# the judge model, so caching would cross-contaminate models).
#
# Memory capture is host-specific (peak VRAM) and is the caller's job — the
# Modal function writes memory.json next to these outputs; this script only
# produces the bench.json / dump per tier. Youden's J is derived downstream.
#
# Usage:
#   QFIRE_BIN=./target/release/qfire \
#   scripts/judge_memory_frontier.sh <ollama-model-tag> <out-dir> [seed]
#
# Example:
#   scripts/judge_memory_frontier.sh llama3.2:1b bench-out/judge_frontier/llama3.2_1b
set -euo pipefail

MODEL="${1:?usage: judge_memory_frontier.sh <model-tag> <out-dir> [seed]}"
OUT="${2:?usage: judge_memory_frontier.sh <model-tag> <out-dir> [seed]}"
SEED="${3:-42}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${QFIRE_BIN:-$ROOT/target/release/qfire}"
CORPORA="${CORPORA_DIR:-$ROOT/corpora/judge_frontier}"
CHAIN="${CHAIN:-judge_scope}"

if [ ! -d "$CORPORA/t1" ]; then
  echo "missing $CORPORA — run scripts/build_judge_frontier_corpora.sh first" >&2
  exit 1
fi

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"   # absolutize before cd, so relative out-dirs still work

# qfire resolves qfire.toml / rules / chains relative to CWD, so run from root.
cd "$ROOT"
echo "judge model: $MODEL  chain: $CHAIN  seed: $SEED  ->  $OUT"

for tier in t1 t2; do
  echo "=== tier $tier ==="
  QFIRE_JUDGE_MODEL="$MODEL" "$BIN" bench --chain "$CHAIN" \
    --attacks "$CORPORA/$tier/attacks" \
    --benign  "$CORPORA/$tier/benign" \
    --seed "$SEED" --no-cache \
    --out  "$OUT/$tier" \
    --dump "$OUT/$tier/dump" 2>&1 | tail -3
done

echo "FRONTIER_RUN_DONE $MODEL"
