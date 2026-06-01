#!/usr/bin/env bash
# E1 adaptive-attack panel. Scores each adaptive attack set through:
#   QFIRE chains + DeBERTa via `qfire bench` (local ONNX), and PromptGuard-2 via
#   baselines.py (only if HF_TOKEN + /tmp/qbase are present). Recall = block_rate
#   on the all-attack set. Benign dir is corpora/eval/benign (classifier FPR only).
set -uo pipefail
cd "$(dirname "$0")/.."
export QFIRE_DEBERTA_DIR=models/deberta
QFIRE=./target/release/qfire
SEED=42
BEN=corpora/eval/benign
OUT=bench-out/adaptive
PG_PY=/tmp/qbase/bin/python

cargo build --release --features onnx
mkdir -p "$OUT"

# adaptive set -> QFIRE scope chain. Uses a case (not an associative array) for
# macOS bash 3.2 compatibility — `declare -A` is unsupported there and errors under set -u.
# healthcare uses scope+PHI (bench_combined); injection uses the positive-security default.
scope_chain_for() {
  case "$1" in
    encoded_injection) echo default ;;
    *) echo bench_combined ;;
  esac
}

# Phase-1 impersonation is healthcare-only (free-form injection camouflage dilutes the
# attack / trips gemma2 safety — see results doc); injection adaptive coverage comes from
# paraphrase_evaded (intent-preserving) + encoded_injection.
for set in impersonation_healthcare paraphrase_evaded encoded_healthcare encoded_injection; do
  ATK="corpora/adaptive/$set"
  [ -f "$ATK/attacks.jsonl" ] || { echo "skip $set (no corpus)"; continue; }
  echo "=== panel: $set ==="
  # QFIRE chains + DeBERTa (local ONNX). bench_phi + judge_scope add detail.
  for chain in bench_deberta "$(scope_chain_for "$set")" bench_phi judge_scope; do
    # Cap the slow LLM judge on the large encoded corpora (1000/929 base64/ROT13
    # gibberish); a 200-prompt sample estimates its block-rate fine. Other chains
    # (sub-ms regex / ONNX deberta) stay full.
    extra=""
    if [ "$chain" = "judge_scope" ]; then
      case "$set" in encoded_*) extra="--limit 200" ;; esac
    fi
    "$QFIRE" bench --chain "$chain" --attacks "$ATK" --benign "$BEN" \
      --seed "$SEED" --no-cache $extra --out "$OUT/${set}__${chain}" >/dev/null 2>&1
  done
  # PromptGuard-2 (+HF DeBERTa) — conditional.
  if [ -n "${HF_TOKEN:-}" ] && [ -x "$PG_PY" ]; then
    "$PG_PY" scripts/baselines.py --attacks "$ATK" --benign "$BEN" \
      --models promptguard-2 --out "$OUT/${set}__promptguard.json" >/dev/null 2>&1 \
      && echo "  promptguard-2 done" || echo "  promptguard-2 FAILED (token/env)"
  else
    echo "  promptguard-2 skipped (no HF_TOKEN or /tmp/qbase)"
  fi
done
echo "ADAPTIVE_PANEL_DONE"
