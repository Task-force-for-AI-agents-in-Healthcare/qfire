#!/usr/bin/env python3
"""Render the cross-model policy-verbosity figure: (a) Youden's J vs rung per
model, (b) per-call latency vs rung per model (log y), (c) J-vs-latency Pareto.
Reuses analyze_cross_model's loaders. Writes paper/figs/policy_length_xmodel.png.

Usage: python3 scripts/plot_cross_model.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import analyze_cross_model as x
import analyze_policy_length as ap

RUNGS = ["t0", "t1", "t2", "t3"]
RUNG_LABELS = ["T0", "T1", "T2", "T3"]
OUT = os.path.join(BASE, "paper/figs/policy_length_xmodel.png")
COLORS = ["#000000", "#4C72B0", "#55A868", "#8172B3", "#C44E52", "#DD8452"]


def collect():
    """Return {model_name: {rung: {j,tpr,tnr,lat}}} pooled across domains."""
    data = {}
    for name, tag, dump_root, lat_root in x.MODELS:
        data[name] = {}
        for rung in RUNGS:
            rows, lats = [], []
            for d in x.DOMAINS:
                r = x.load_dump_rows(dump_root, d, rung)
                if r:
                    rows.extend(r)
                lats.append(x.chain_latency(lat_root, d, rung))
            if not rows:
                continue
            m = ap.metrics(rows)
            data[name][rung] = {"j": m["youden_j"], "tpr": m["tpr"],
                                "tnr": m["tnr"], "lat": x.pooled_latency(lats)}
    return data


def main():
    data = collect()
    xs = list(range(4))
    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(15, 4.4))

    for ci, (name, series) in enumerate(data.items()):
        c = COLORS[ci % len(COLORS)]
        js = [series.get(r, {}).get("j") for r in RUNGS]
        ls = [series.get(r, {}).get("lat") for r in RUNGS]
        axA.plot(xs, js, marker="o", lw=2, color=c, label=name)
        if any(v is not None for v in ls):
            axB.plot(xs, ls, marker="o", lw=2, color=c, label=name)
        for ri, r in enumerate(RUNGS):
            s = series.get(r)
            if s and s["lat"] is not None:
                axC.scatter(s["lat"], s["j"], color=c, s=40)
                axC.annotate(RUNG_LABELS[ri], (s["lat"], s["j"]),
                             textcoords="offset points", xytext=(4, 3), fontsize=7)

    axA.set_xticks(xs); axA.set_xticklabels(RUNG_LABELS)
    axA.set_ylabel("Youden's J"); axA.set_title("(a) Accuracy vs policy length")
    axA.grid(True, alpha=0.3); axA.legend(fontsize=8)

    axB.set_xticks(xs); axB.set_xticklabels(RUNG_LABELS)
    axB.set_yscale("log")
    axB.set_ylabel("mean ms / call (log)"); axB.set_title("(b) Latency vs policy length")
    axB.grid(True, alpha=0.3, which="both"); axB.legend(fontsize=8)

    axC.set_xlabel("mean ms / call"); axC.set_ylabel("Youden's J")
    axC.set_title("(c) Quality-vs-latency (all model×rung)")
    axC.grid(True, alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
