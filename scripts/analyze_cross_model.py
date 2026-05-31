#!/usr/bin/env python3
"""Cross-model policy-verbosity analysis. For each model × rung (pooled across the
4 domains): accuracy (TPR/TNR/over-refusal/J) from the dumps, and per-call latency
(mean_detector_ms) from each run's bench.json. Writes
bench-out/policy_length_xmodel/results.md.

llama3.2 reads from bench-out/policy_length_llama3.2/ (sliced dumps) for accuracy
and from the ORIGINAL full bench-out/policy_length/<domain>/bench.json for latency
(per-call latency is corpus-size-independent).

Usage: python3 scripts/analyze_cross_model.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import analyze_policy_length as ap  # reuse metrics()

DOMAINS = ["marketing", "healthcare", "code", "sql"]
RUNGS = ["t0", "t1", "t2", "t3"]
OUT_DIR = os.path.join(BASE, "bench-out/policy_length_xmodel")

# (display name, tag, dump-root, latency-bench-root)
MODELS = [
    ("llama3.2", "llama3.2:latest", "bench-out/policy_length_llama3.2", "bench-out/policy_length"),
    ("phi3.5:3.8b", "phi3.5:3.8b", "bench-out/policy_length_phi3.5_3.8b", "bench-out/policy_length_phi3.5_3.8b"),
    ("llama3.1:8b", "llama3.1:8b", "bench-out/policy_length_llama3.1_8b", "bench-out/policy_length_llama3.1_8b"),
    ("gemma2:9b", "gemma2:9b", "bench-out/policy_length_gemma2_9b", "bench-out/policy_length_gemma2_9b"),
    ("gemma4", "gemma4:latest", "bench-out/policy_length_gemma4", "bench-out/policy_length_gemma4"),
    ("deepseek-r1", "deepseek-r1:latest", "bench-out/policy_length_deepseek_r1", "bench-out/policy_length_deepseek_r1"),
]


def pooled_latency(vals):
    """Mean of per-domain mean_detector_ms, ignoring None."""
    xs = [v for v in vals if v is not None]
    return sum(xs) / len(xs) if xs else None


def load_dump_rows(dump_root, domain, rung):
    path = os.path.join(BASE, dump_root, domain, "dump", f"pl_{domain}_{rung}.jsonl")
    if not os.path.exists(path):
        return None
    return [json.loads(l) for l in open(path) if l.strip()]


def chain_latency(bench_root, domain, rung):
    """mean_detector_ms for chain pl_<domain>_<rung> from a domain's bench.json."""
    path = os.path.join(BASE, bench_root, domain, "bench.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    cid = f"pl_{domain}_{rung}"
    for r in d.get("reports", []):
        if r.get("chain") == cid:
            return r["overall"].get("mean_detector_ms")
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = ["# Cross-Model Policy-Verbosity Ablation — Results", "",
             "300-attack seeded subset + 50 in-domain benign/domain, judge-only, "
             "--no-cache, seed 42. J = TPR + TNR - 1. Latency = mean per-call "
             "detector ms (judge-only), averaged across domains.", "",
             "| model | rung | TPR | TNR | over-refusal | J | latency (ms/call) |",
             "|---|---|---|---|---|---|---|"]
    # collect for the figure-feed print at the end
    summary = {}
    for name, tag, dump_root, lat_root in MODELS:
        summary[name] = {}
        for rung in RUNGS:
            pooled_rows, lats = [], []
            for d in DOMAINS:
                rows = load_dump_rows(dump_root, d, rung)
                if rows:
                    pooled_rows.extend(rows)
                lats.append(chain_latency(lat_root, d, rung))
            if not pooled_rows:
                lines.append(f"| {name} | {rung} | — | — | — | — | (no dumps) |")
                continue
            m = ap.metrics(pooled_rows)
            lat = pooled_latency(lats)
            lat_s = f"{lat:.0f}" if lat is not None else "—"
            summary[name][rung] = {"j": m["youden_j"], "tpr": m["tpr"],
                                   "tnr": m["tnr"], "lat": lat}
            lines.append(f"| {name} | {rung} | {m['tpr']:.3f} | {m['tnr']:.3f} | "
                         f"{m['over_refusal']:.3f} | {m['youden_j']:+.3f} | {lat_s} |")
    out = os.path.join(OUT_DIR, "results.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out)
    print("ANALYZE_XMODEL_DONE")


if __name__ == "__main__":
    main()
