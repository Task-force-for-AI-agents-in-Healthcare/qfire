#!/usr/bin/env python3
"""Tabulate the judge-model ablation: per-model precision/recall/F1/FPR on the
hipaa_phi chain over the HealthBench judge subset, plus agreement (and Cohen's
kappa) of each model's per-prompt block decisions against the llama3.1 baseline.

Reads bench-out/judge_abl/<safe>/bench.json and the per-prompt dumps
bench-out/judge_abl/dump_<safe>/hipaa_phi.jsonl.
"""
import glob
import json
import os

BASE = "/Users/jim/Desktop/qfire"
# Which ablation output dir to analyze: judge_scope (single-rule, discriminating)
# by default; pass a chain name as argv[1] (e.g. hipaa_phi) to inspect another.
import sys as _sys
_CHAIN = _sys.argv[1] if len(_sys.argv) > 1 else "judge_scope"
ABL = os.path.join(BASE, f"bench-out/judge_abl_{_CHAIN}")
if not os.path.isdir(ABL) and os.path.isdir(os.path.join(BASE, "bench-out/judge_abl")):
    ABL = os.path.join(BASE, "bench-out/judge_abl")  # legacy fallback

# Auto-discover whichever models the ablation actually ran (one subdir per model,
# named by the sanitized tag), keeping the llama3.1 baseline first.
def discover():
    safes = sorted(
        d for d in os.listdir(ABL)
        if os.path.isdir(os.path.join(ABL, d)) and not d.startswith("dump_")
    )
    def label(s):
        return s.replace("___", ":").replace("__", ":").replace("_", ".")
    base = [s for s in safes if s.startswith("llama3")]
    rest = [s for s in safes if not s.startswith("llama3")]
    ordered = base + rest
    return [(s, label(s) + (" (baseline)" if s in base[:1] else "")) for s in ordered]


MODELS = discover() if os.path.isdir(ABL) else []


def load_metrics(safe):
    p = os.path.join(ABL, safe, "bench.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    for r in d["reports"]:
        if r["chain"] == "hipaa_phi":
            return r["overall"]
    return d["reports"][0]["overall"] if d.get("reports") else None


def load_decisions(safe):
    # dump file name follows the chain id
    cand = glob.glob(os.path.join(ABL, f"dump_{safe}", "*.jsonl"))
    if not cand:
        return None
    rows = [json.loads(l) for l in open(cand[0]) if l.strip()]
    return [(bool(r["is_attack"]), bool(r["blocked"])) for r in rows]


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def main():
    print("=== Judge-model ablation: hipaa_phi chain, HealthBench judge subset ===\n")
    hdr = f"{'model':28s} {'P':>6s} {'R':>6s} {'F1':>6s} {'FPR':>6s} {'block':>6s}"
    print(hdr)
    print("-" * len(hdr))
    metrics = {}
    for safe, label in MODELS:
        m = load_metrics(safe)
        metrics[safe] = m
        if m is None:
            print(f"{label:28s} {'(missing)':>6s}")
            continue
        print(f"{label:28s} {m['precision']:6.3f} {m['recall']:6.3f} "
              f"{m['f1']:6.3f} {m['fpr']:6.3f} {m.get('block_rate', float('nan')):6.3f}")

    # Agreement vs baseline
    base_safe = MODELS[0][0]
    base = load_decisions(base_safe)
    print("\n=== Per-prompt decision agreement vs llama3.1 baseline ===\n")
    if base is None:
        print("(baseline dump missing)")
        return
    base_block = [b for _, b in base]
    h2 = f"{'model':28s} {'agree%':>8s} {'kappa':>7s} {'n':>5s}"
    print(h2)
    print("-" * len(h2))
    for safe, label in MODELS:
        dec = load_decisions(safe)
        if dec is None:
            print(f"{label:28s} {'(missing)':>8s}")
            continue
        blk = [b for _, b in dec]
        n = min(len(blk), len(base_block))
        agree = sum(1 for i in range(n) if blk[i] == base_block[i]) / n if n else float("nan")
        k = kappa(base_block[:n], blk[:n])
        print(f"{label:28s} {agree*100:7.1f}% {k:7.3f} {n:5d}")
    print("\nJUDGE_ABL_ANALYSIS_DONE")


if __name__ == "__main__":
    main()
