#!/usr/bin/env bash
# Judge-model ablation: does swapping the LLM behind the scope-judge node change
# firewall performance? Reuses the EXACT HealthBench LLM-ablation setup from
# scripts/healthbench_run.sh (the hipaa_phi expression chain over a 100/100
# HealthBench subset, seed 42), varying only the model via QFIRE_JUDGE_MODEL.
#
# Limitation (documented in the paper): the user asked for qwen3.5 / gemma-4,
# which are not available on Ollama. We use the closest installed cross-family
# models. qwen3-coder is coding-tuned and included as a Qwen-family data point
# with that caveat.
set +e
cd "$(dirname "$0")/.." || exit 1
export QFIRE_DEBERTA_DIR=models/deberta
BIN=./target/release/qfire
HB=corpora/healthcare_bench

# Same subset construction as healthbench_run.sh (judge subset).
mkdir -p "$HB/subset/attacks" "$HB/subset/benign"
head -100 "$HB/attacks/attacks.jsonl" > "$HB/subset/attacks/a.jsonl"
head -100 "$HB/benign/benign.jsonl"  > "$HB/subset/benign/b.jsonl"

# Judge models to compare. Pass exact Ollama tags as args, e.g.:
#   scripts/judge_model_ablation.sh llama3.1:8b qwen3.6:latest gemma4:latest
# Defaults to the baseline + whatever qwen*/gemma* tags are currently installed.
if [ "$#" -gt 0 ]; then
  MODELS="$*"
else
  EXTRA=$(ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -Ei '^(qwen|gemma)' | tr '\n' ' ')
  MODELS="llama3.1:8b $EXTRA"
fi
echo "models under test: $MODELS"

# CHAIN to ablate over. Default is the single-rule judge_scope chain (which
# discriminates between models); pass CHAIN=hipaa_phi to reproduce the saturated
# full-chain run. Output dir is namespaced by chain so both can coexist.
CHAIN="${CHAIN:-judge_scope}"
OUTROOT="bench-out/judge_abl_${CHAIN}"

mkdir -p "$OUTROOT"
echo "chain under test: $CHAIN  ->  $OUTROOT"
for m in $MODELS; do
  safe=$(echo "$m" | tr ':/.' '___')
  echo "=== judge model: $m ==="
  QFIRE_JUDGE_MODEL="$m" $BIN bench --chain "$CHAIN" \
    --attacks "$HB/subset/attacks" --benign "$HB/subset/benign" \
    --seed 42 --no-cache \
    --out "$OUTROOT/$safe" \
    --dump "$OUTROOT/dump_$safe" 2>&1 | tail -2
  echo "JABL_DONE_$safe"
done
echo "JUDGE_ABL_ALL_DONE"
