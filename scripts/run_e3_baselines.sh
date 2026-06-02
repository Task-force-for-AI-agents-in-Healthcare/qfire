#!/usr/bin/env bash
# E3: score qualifire/prompt-injection-sentinel (HF, gated -> needs HF_TOKEN) + a bare
# LLM-judge (llama3.1:8b via Ollama) on the two main corpora, into the baseline JSONs
# make_tables.py reads. Run the bare-judge pass when no other Ollama-heavy job is active.
# Requires HF_TOKEN exported for the gated Sentinel download.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python3
[ -x /tmp/qbase/bin/python ] && PY=/tmp/qbase/bin/python
: "${HF_TOKEN:?set HF_TOKEN (gated Sentinel repo) before running}"
echo "== public injection =="
$PY scripts/baselines.py --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --models "sentinel,llm-judge" --out bench-out/baselines_e3_injection.json
echo "== QFIRE-HealthBench =="
$PY scripts/baselines.py --attacks corpora/healthcare_bench/attacks --benign corpora/healthcare_bench/benign \
  --models "sentinel,llm-judge" --out bench-out/baselines_e3_healthbench.json
echo "E3_BASELINES_DONE"
