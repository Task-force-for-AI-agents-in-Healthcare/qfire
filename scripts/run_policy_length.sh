#!/usr/bin/env bash
# Policy-verbosity ablation runner. One bench per domain (4 rungs as 4 chains),
# shared attack corpus + per-domain in-domain benign. --no-cache is REQUIRED:
# all rungs share a verdict-cache key (scope is not part of the key), so caching
# would make rungs T1-T3 reuse T0's verdict. See the plan's constraints section.
set -euo pipefail
cd "$(dirname "$0")/.."

QFIRE=./target/release/qfire
SEED=42
ATTACKS=corpora/eval/attacks
OUTROOT=bench-out/policy_length

cargo build --release

for d in marketing healthcare code sql; do
  echo "=== domain: $d ==="
  OUT="$OUTROOT/$d"
  mkdir -p "$OUT/dump"
  "$QFIRE" bench \
    --chain pl_${d}_t0 --chain pl_${d}_t1 --chain pl_${d}_t2 --chain pl_${d}_t3 \
    --attacks "$ATTACKS" \
    --benign "corpora/policy_length/$d/benign" \
    --seed "$SEED" \
    --no-cache \
    --dump "$OUT/dump" \
    --out "$OUT"
done
echo "RUN_DONE"
