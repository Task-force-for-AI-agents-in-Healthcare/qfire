#!/usr/bin/env bash
# Build the two difficulty tiers for the judge memory-vs-J frontier experiment.
#
# The judge node (the only model-size-sensitive detector) is isolated by the
# single-rule `judge_scope` chain (hc_no_diagnosis). We evaluate every judge
# model on two tiers that share the SAME benign in-scope clinical requests
# (the negatives) but differ in attack difficulty (the positives):
#
#   T1 (standard): the plain HealthBench attacks  -> near-saturation; small
#                  judges already do well, so the frontier sits at low memory.
#   T2 (hard):     adaptive healthcare evasions (impersonation + base64-encoded
#                  exfiltration) -> small judges degrade, pushing the frontier
#                  to higher memory.
#
# Youden's J = TPR - FPR is computed per (model, tier) downstream; the shared
# benign set keeps FPR comparable across tiers, so a tier difference is purely
# an attack-detection (TPR) effect.
#
# Deterministic: fixed `head` slices, no shuffling. Re-running reproduces byte
# for byte. Output: corpora/judge_frontier/{t1,t2}/{attacks,benign}/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HB="$ROOT/corpora/healthcare_bench"
ADV="$ROOT/corpora/adaptive"
OUT="${OUT_DIR:-$ROOT/corpora/judge_frontier}"

# How many of each class to take (kept modest so a full model+quant sweep is
# cheap; class imbalance is fine because J scores TPR and FPR within-class).
N_BENIGN="${N_BENIGN:-100}"
N_T1_ATTACK="${N_T1_ATTACK:-100}"
N_IMPERSONATION="${N_IMPERSONATION:-120}"   # all of impersonation_healthcare
N_ENCODED="${N_ENCODED:-80}"                # slice of encoded_healthcare

# Guard the rm: refuse an empty or filesystem-root target before wiping.
case "$OUT" in
  ""|"/"|"/.") echo "refusing to rm unsafe OUT='$OUT'" >&2; exit 1 ;;
esac
rm -rf "$OUT"
mkdir -p "$OUT/t1/attacks" "$OUT/t1/benign" "$OUT/t2/attacks" "$OUT/t2/benign"

# Shared negatives: legitimate in-scope clinical requests.
head -n "$N_BENIGN" "$HB/benign/benign.jsonl" > "$OUT/t1/benign/benign.jsonl"
cp "$OUT/t1/benign/benign.jsonl" "$OUT/t2/benign/benign.jsonl"

# T1 positives: plain HealthBench attacks.
head -n "$N_T1_ATTACK" "$HB/attacks/attacks.jsonl" > "$OUT/t1/attacks/attacks.jsonl"

# T2 positives: adaptive healthcare evasions (harder to recognize as out-of-scope).
{
  head -n "$N_IMPERSONATION" "$ADV/impersonation_healthcare/attacks.jsonl"
  head -n "$N_ENCODED"       "$ADV/encoded_healthcare/attacks.jsonl"
} > "$OUT/t2/attacks/attacks.jsonl"

echo "built tiers under $OUT"
for t in t1 t2; do
  a=$(wc -l < "$OUT/$t/attacks/attacks.jsonl")
  b=$(wc -l < "$OUT/$t/benign/benign.jsonl")
  echo "  $t: $a attacks / $b benign"
done
