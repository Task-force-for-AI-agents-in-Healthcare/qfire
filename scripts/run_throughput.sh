#!/usr/bin/env bash
# E2 throughput/scaling runner. Deterministic detectors only (no judge).
# A: latency vs #rules (wall vs summed) at engine-concurrency 1 and 16.
# B: QPS vs in-flight load-concurrency on the deterministic hybrid chain.
# C: short-circuit savings (sc_gated vs sc_always).
set -uo pipefail
cd "$(dirname "$0")/.."
export QFIRE_DEBERTA_DIR=models/deberta
QFIRE=./target/release/qfire
SEED=42
OUT=bench-out/throughput
ATTACKS=corpora/eval/attacks
BENIGN=corpora/eval/benign
REPS=3

cargo build --release --features onnx   # real ONNX deberta (the expensive node); without this it falls back to a sub-ms lexical stub and Parts A/C are meaningless
mkdir -p "$OUT"
echo "cores: $(sysctl -n hw.ncpu 2>/dev/null || nproc)" | tee "$OUT/machine.txt"

# --- Part A: rule fan-out (benign corpus so nothing short-circuits) ---
KS=$(ls chains/bench/scaling/ | grep -oE 'scale_k[0-9]+' | sort -u)
for ec in 1 16; do
  for k in $KS; do
    for rep in $(seq 1 $REPS); do
      # --limit caps prompts: Part A is deberta-fanout heavy (17/21 rules carry a
      # deberta node, no short-circuit on benign), so the full corpus would take
      # hours; per-prompt latency medians are stable well under 100 prompts.
      "$QFIRE" bench --chain "$k" --attacks "$BENIGN" --benign "$BENIGN" \
        --seed "$SEED" --no-cache --engine-concurrency "$ec" --limit 100 \
        --out "$OUT/A_${k}_ec${ec}_r${rep}" >/dev/null 2>&1
    done
  done
done
echo "Part A done"

# --- Part B: throughput vs load-concurrency (attacks; hybrid deterministic chain) ---
for n in 1 2 4 8 16 32 64; do
  for rep in $(seq 1 $REPS); do
    "$QFIRE" bench --chain bench_hybrid --attacks "$ATTACKS" --benign "$BENIGN" \
      --seed "$SEED" --no-cache --load-concurrency "$n" \
      --out "$OUT/B_n${n}_r${rep}" >/dev/null 2>&1
  done
done
echo "Part B done"

# --- Part C: short-circuit savings ---
for c in sc_gated sc_always; do
  "$QFIRE" bench --chain "$c" --attacks "$ATTACKS" --benign "$BENIGN" \
    --seed "$SEED" --no-cache --dump "$OUT/C_${c}/dump" --out "$OUT/C_${c}" >/dev/null 2>&1
done
echo "Part C done"

# --- Part A-IO: I/O-bound fan-out (judge nodes; needs a running Ollama with the
# default judge model). Concurrent judge (network) calls overlap, so wall << summed
# at engine-concurrency 16 — the parallel payoff that CPU-bound deberta (Part A)
# cannot get. Small --limit since each judge call is ~1-2 s. ---
IO_BEN=corpora/policy_length/marketing/benign
if command -v ollama >/dev/null 2>&1; then
  for ec in 1 16; do
    for k in 1 2 4 8 16; do
      for rep in $(seq 1 $REPS); do
        "$QFIRE" bench --chain "judge_k$k" --attacks "$IO_BEN" --benign "$IO_BEN" \
          --seed "$SEED" --no-cache --engine-concurrency "$ec" --limit 3 \
          --out "$OUT/A_io_judge_k${k}_ec${ec}_r${rep}" >/dev/null 2>&1
      done
    done
  done
  echo "Part A-IO done"
else
  echo "Part A-IO skipped (no ollama)"
fi
echo "THROUGHPUT_RUN_DONE"
