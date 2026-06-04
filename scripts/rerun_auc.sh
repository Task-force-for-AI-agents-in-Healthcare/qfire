#!/usr/bin/env bash
# Rebuild with the corrected AUC score aggregation and re-run exp1 + exp2,
# then regenerate tables and print the new F1/AUC per chain.
set +e
cd "$(dirname "$0")/.." || exit 1
export QFIRE_DEBERTA_DIR=models/deberta
echo "== build --features onnx =="
cargo build --release --features onnx 2>&1 | tail -3
echo "BUILD_DONE rc=${PIPESTATUS[0]}"
BIN=./target/release/qfire
echo "== exp1 =="
$BIN bench --chain bench_regex --chain bench_aho --chain bench_deberta \
  --chain bench_entropy --chain bench_hybrid --chain bench_hybrid_norm \
  --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --seed 42 --out bench-out/exp1 2>&1 | tail -2
echo "== exp2 =="
$BIN bench --chain bench_hybrid --chain bench_hybrid_norm \
  --attacks corpora/eval/attacks_obf --benign corpora/eval/benign \
  --seed 42 --out bench-out/exp2 2>&1 | tail -2
echo "== tables =="
python3 scripts/make_tables.py 2>&1 | tail -1
echo "== AUC check =="
python3 -c "
import json
for e in ['exp1','exp2']:
    d=json.load(open(f'bench-out/{e}/bench.json'))
    print('---',e)
    for r in d['reports']:
        m=r['overall']; print('%-22s F1=%.3f AUC=%.3f'%(r['chain'],m['f1'],m['auc']))
"
echo "RERUN_DONE"
