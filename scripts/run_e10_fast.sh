#!/usr/bin/env bash
# E10: fast-classifier tier (hlyn-labs DeBERTa-70M INT8 ONNX + PromptGuard-2 22M) on both
# main corpora. CPU-only (no Ollama). Requires HF_TOKEN (gated PromptGuard-2 + hlyn download).
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python3; [ -x /tmp/qbase/bin/python ] && PY=/tmp/qbase/bin/python
: "${HF_TOKEN:?set HF_TOKEN}"
echo "== public injection =="
$PY scripts/baselines.py --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --models "deberta-70m,promptguard-2-22m" --out bench-out/baselines_e10_injection.json
echo "== QFIRE-HealthBench =="
$PY scripts/baselines.py --attacks corpora/healthcare_bench/attacks --benign corpora/healthcare_bench/benign \
  --models "deberta-70m,promptguard-2-22m" --out bench-out/baselines_e10_healthbench.json
echo "E10_FAST_DONE"
