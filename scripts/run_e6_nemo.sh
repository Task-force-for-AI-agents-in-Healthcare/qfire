#!/usr/bin/env bash
# E6: run the NeMo Guardrails full-stack baseline on both main corpora (stratified sample)
# and the 4 E1 adaptive sets (attack-only recall). Offline (Ollama /v1 + local Presidio/gpt2).
# Uses the dedicated E6 venv. Serialize with other Ollama-heavy runs.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv-e6/bin/python
SAMPLE="${SAMPLE:-400}"      # per-class sample for the big main corpora
ASAMPLE="${ASAMPLE:-200}"    # per-set cap for the large adaptive sets
SEED=42
mkdir -p bench-out/adaptive

echo "== main corpora (stratified ${SAMPLE}/${SAMPLE}) =="
$PY scripts/run_nemo.py --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --sample "$SAMPLE" --seed $SEED --out bench-out/nemo_eval.json
$PY scripts/run_nemo.py --attacks corpora/healthcare_bench/attacks --benign corpora/healthcare_bench/benign \
  --sample "$SAMPLE" --seed $SEED --out bench-out/nemo_healthbench.json

echo "== adaptive sets (attack-only recall, cap ${ASAMPLE}) =="
for s in encoded_injection encoded_healthcare impersonation_healthcare paraphrase_evaded; do
  $PY scripts/run_nemo.py --attacks "corpora/adaptive/$s/attacks.jsonl" --recall-only \
    --sample "$ASAMPLE" --seed $SEED --out "bench-out/adaptive/${s}__nemo.json"
done
echo "E6_ALL_DONE"
