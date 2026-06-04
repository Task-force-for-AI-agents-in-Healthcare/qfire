#!/usr/bin/env bash
# Benchmark QFIRE on HealthBench + read the de-obfuscation (mirror vs independent)
# results, and per-category recall.
set +e
cd "$(dirname "$0")/.." || exit 1
export QFIRE_DEBERTA_DIR=models/deberta
BIN=./target/release/qfire
HB=corpora/healthcare_bench

echo "== lint =="; $BIN rules lint 2>&1 | tail -2

echo "== deterministic chains on full HealthBench (2000) =="
$BIN bench --chain bench_deberta --chain bench_hybrid --chain bench_hybrid_trig \
  --chain bench_phi --chain bench_combined --chain bench_combined_trig \
  --attacks $HB/attacks --benign $HB/benign \
  --seed 42 --out bench-out/healthbench --dump bench-out/hb_dump --no-cache 2>&1 | tail -2
echo "HB_DET_DONE"

echo "== judge-scope subset (100/100) =="
mkdir -p $HB/subset/attacks $HB/subset/benign
head -100 $HB/attacks/attacks.jsonl > $HB/subset/attacks/a.jsonl
head -100 $HB/benign/benign.jsonl  > $HB/subset/benign/b.jsonl
$BIN bench --chain hipaa_phi --attacks $HB/subset/attacks --benign $HB/subset/benign \
  --seed 42 --out bench-out/healthbench_judge 2>&1 | tail -2
echo "HB_JUDGE_DONE"

echo "== HealthBench overall (deterministic chains) =="
python3 -c "
import json
d=json.load(open('bench-out/healthbench/bench.json'))
for r in d['reports']:
    m=r['overall']; print('%-22s P=%.3f R=%.3f F1=%.3f FPR=%.3f'%(r['chain'],m['precision'],m['recall'],m['f1'],m['fpr']))
"
echo "== HealthBench judge chain =="
python3 -c "
import json
d=json.load(open('bench-out/healthbench_judge/bench.json'))
for r in d['reports']:
    m=r['overall']; print('%-22s block=%.3f FPR=%.3f P=%.3f R=%.3f F1=%.3f'%(r['chain'],m['block_rate'],m['fpr'],m['precision'],m['recall'],m['f1']))
"
echo "== per-category recall =="
python3 scripts/healthbench_percat.py 2>&1 | tail -22

echo "== de-obf: MIRROR vs INDEPENDENT obfuscator =="
python3 -c "
import json
for tag,path in [('mirror','bench-out/exp2/bench.json'),('independent','bench-out/exp2_indep/bench.json')]:
    d=json.load(open(path))
    print('---',tag,'obfuscator')
    for r in d['reports']:
        m=r['overall']; print('  %-20s recall=%.3f F1=%.3f FPR=%.3f'%(r['chain'],m['recall'],m['f1'],m['fpr']))
"
echo "HB_ALL_DONE"
