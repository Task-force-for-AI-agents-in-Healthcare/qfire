#!/usr/bin/env bash
# Run the full QFIRE paper experiment matrix end-to-end with the real DeBERTa
# ONNX binary, then the Python baselines, then generate the LaTeX tables.
set +e
cd "$(dirname "$0")/.." || exit 1
export QFIRE_DEBERTA_DIR=models/deberta
BIN=./target/release/qfire
SEED=42

echo "== EXP1: detector matrix (public corpus, real DeBERTa ONNX) =="
$BIN bench \
  --chain bench_regex --chain bench_aho --chain bench_deberta \
  --chain bench_entropy --chain bench_hybrid --chain bench_hybrid_norm \
  --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --seed $SEED --out bench-out/exp1 2>&1 | tail -2
echo "EXP1_DONE"

echo "== EXP2: de-obfuscation ablation (obfuscated attacks) =="
$BIN bench \
  --chain bench_hybrid --chain bench_hybrid_norm \
  --attacks corpora/eval/attacks_obf --benign corpora/eval/benign \
  --seed $SEED --out bench-out/exp2 2>&1 | tail -2
echo "EXP2_DONE"

echo "== EXP3: healthcare / PHI panel (uses Ollama judge; slower) =="
$BIN bench \
  --chain hipaa_phi \
  --attacks corpora/healthcare/attacks --benign corpora/healthcare/benign \
  --seed $SEED --out bench-out/healthcare 2>&1 | tail -2
echo "HC_DONE"

echo "== BASELINES: open Python detectors (deberta, promptguard-2) =="
python3 scripts/baselines.py 2>&1 | tail -10
echo "BASE_DONE"

echo "== TABLES =="
python3 scripts/make_tables.py 2>&1 | tail -3
echo "ALL_EXPERIMENTS_DONE"
