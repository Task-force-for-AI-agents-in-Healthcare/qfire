#!/usr/bin/env bash
# Cross-model policy-verbosity ablation. For each judge model (except llama3.2,
# which is reused via slice_llama32_dumps.py), run the 16 conditions on the shared
# 300-attack subset + 50 in-domain benign/domain, varying only QFIRE_JUDGE_MODEL.
# --no-cache is REQUIRED (the verdict cache key omits scope). Latency is captured
# in each run's bench.json (mean_detector_ms; judge-only => ~judge call time).
set -uo pipefail
cd "$(dirname "$0")/.."

QFIRE=./target/release/qfire
SEED=42
ATTACKS=corpora/policy_length/attacks_subset

cargo build --release

# tag -> output slug
run_model() {
  local tag="$1" slug="$2"
  echo "=================== model: $tag ($slug) ==================="
  for d in marketing healthcare code sql; do
    echo "--- $slug / $d ---"
    local OUT="bench-out/policy_length_${slug}/$d"
    mkdir -p "$OUT/dump"
    QFIRE_JUDGE_MODEL="$tag" "$QFIRE" bench \
      --chain pl_${d}_t0 --chain pl_${d}_t1 --chain pl_${d}_t2 --chain pl_${d}_t3 \
      --attacks "$ATTACKS" \
      --benign "corpora/policy_length/$d/benign" \
      --seed "$SEED" \
      --no-cache \
      --dump "$OUT/dump" \
      --out "$OUT"
  done
}

run_model "phi3.5:3.8b"  "phi3.5_3.8b"
run_model "llama3.1:8b"  "llama3.1_8b"
run_model "gemma2:9b"    "gemma2_9b"
run_model "gemma4:latest" "gemma4"
run_model "deepseek-r1:latest" "deepseek_r1"
echo "XMODEL_RUN_DONE"
