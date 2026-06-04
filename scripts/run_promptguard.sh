#!/usr/bin/env bash
# Run Meta Llama-Prompt-Guard-2 (+ PromptGuard-1) head-to-head on the SAME
# corpora QFIRE is evaluated on. Token is read from HF_TOKEN in the environment.
set +e
cd "$(dirname "$0")/.." || exit 1
PY=/tmp/qbase/bin/python
export TOKENIZERS_PARALLELISM=false

if [ -z "$HF_TOKEN" ]; then echo "ERROR: HF_TOKEN not set"; exit 2; fi

echo "== [1/2] public eval corpus (984/984) — merge into baselines.json =="
$PY scripts/baselines.py \
  --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --models promptguard-2,promptguard-1 \
  --out bench-out/baselines.json --load-existing 2>&1 | tail -40
echo "PG_EVAL_DONE"

echo "== [2/2] QFIRE-HealthBench (1000/1000) — full healthcare baseline table =="
$PY scripts/baselines.py \
  --attacks corpora/healthcare_bench/attacks --benign corpora/healthcare_bench/benign \
  --models all \
  --out bench-out/baselines_healthbench.json 2>&1 | tail -40
echo "PG_HB_DONE"
echo "PROMPTGUARD_ALL_DONE"
