#!/usr/bin/env bash
# Round-2 experiments addressing the peer review:
#  - paired statistics (per-prompt dump for McNemar / bootstrap F1 CI)
#  - de-contaminated held-out evaluation (deepset removed)
#  - triggered de-obfuscation vs always-on, on mirror AND independent obfuscators
#  - honest per-chain latency (--no-cache) + measured parallel fan-out speedup
set +e
cd "$(dirname "$0")/.." || exit 1
export QFIRE_DEBERTA_DIR=models/deberta
BIN=./target/release/qfire
SEED=42

echo "== prep corpora =="
python3 scripts/decontaminate.py 2>&1 | tail -1
python3 scripts/obfuscate_independent.py 2>&1 | tail -1

echo "== EXP1: full matrix + per-prompt dump + honest latency (--no-cache) =="
$BIN bench --chain bench_regex --chain bench_aho --chain bench_deberta \
  --chain bench_entropy --chain bench_hybrid --chain bench_hybrid_norm --chain bench_hybrid_trig \
  --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --seed $SEED --out bench-out/exp1 --dump bench-out/dump1 --no-cache 2>&1 | tail -2
echo "EXP1_DONE"

echo "== HELD-OUT: deepset removed (generalization for DeBERTa) =="
$BIN bench --chain bench_deberta --chain bench_hybrid \
  --attacks corpora/eval_heldout/attacks --benign corpora/eval_heldout/benign \
  --seed $SEED --out bench-out/heldout 2>&1 | tail -2
echo "HELDOUT_DONE"

echo "== EXP2a: MIRROR obfuscator {off, always, triggered} =="
$BIN bench --chain bench_hybrid --chain bench_hybrid_norm --chain bench_hybrid_trig \
  --attacks corpora/eval/attacks_obf --benign corpora/eval/benign \
  --seed $SEED --out bench-out/exp2 2>&1 | tail -2
echo "EXP2_DONE"

echo "== EXP2b: INDEPENDENT obfuscator {off, always, triggered} =="
$BIN bench --chain bench_hybrid --chain bench_hybrid_norm --chain bench_hybrid_trig \
  --attacks corpora/eval/attacks_obf_indep --benign corpora/eval/benign \
  --seed $SEED --out bench-out/exp2_indep 2>&1 | tail -2
echo "EXP2INDEP_DONE"

echo "== PAIRED STATS (hybrid vs deberta) =="
python3 scripts/analyze_paired.py bench-out/dump1 bench_deberta bench_hybrid 2>&1 | tail -8

echo "== PARALLEL FAN-OUT speedup (from healthcare 10-rule chain) =="
python3 -c "
import json
try:
    d=json.load(open('bench-out/healthcare/bench.json')); m=d['reports'][0]['overall']
    print('parallel fan-out: mean_detector=%.0fms wall=%.0fms speedup=%.1fx'%(m['mean_detector_ms'],m['mean_wall_ms'],m['mean_detector_ms']/max(m['mean_wall_ms'],1e-6)))
except Exception as e: print('healthcare parallel readout NA:',e)
"
echo "== regenerate tables =="
python3 scripts/make_tables.py 2>&1 | tail -1
echo "ALL_REBUTTAL_DONE"
