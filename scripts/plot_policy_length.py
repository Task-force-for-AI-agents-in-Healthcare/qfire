#!/usr/bin/env python3
"""Render the policy-verbosity ablation figure for the paper from the per-prompt
dumps in bench-out/policy_length/. Two panels:
  (left)  Youden's J vs rung, one line per domain + bold pooled — shows the
          non-monotone curve (T1 dip, T2 peak, T3 regression).
  (right) Pooled TPR (attacks blocked) vs TNR (legit passed) across rungs —
          shows TPR is ~flat while TNR carries all the variation.
Writes paper/figs/policy_length.png.

Usage: python3 scripts/plot_policy_length.py
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import analyze_policy_length as a  # reuse metrics()/load_dump()

DOMAINS = ["marketing", "healthcare", "code", "sql"]
RUNGS = ["t0", "t1", "t2", "t3"]
RUNG_LABELS = ["T0\nterse", "T1\nsentence", "T2\nparagraph", "T3\nfirewall"]
OUT = os.path.join(BASE, "paper/figs/policy_length.png")


# Cached series for when the raw per-prompt dumps in bench-out/policy_length/ are
# not present (they are gitignored and not part of the published artifact). The
# pooled J / TPR / TNR rows below are the exact published values (see §verbabl and
# Fig. 14b); the per-domain Youden's J rows were recovered from the rendered figure
# paper/figs/policy_length.png. The script prefers recomputing from dumps when they
# exist and only falls back to these constants otherwise — so layout edits here do
# not silently change the reported numbers.
FALLBACK_J = {
    "marketing":  [0.967, 0.977, 0.985, 0.970],
    "healthcare": [0.480, 0.060, 0.460, 0.353],
    "code":       [0.955, 0.895, 0.986, 0.912],
    "sql":        [0.774, 0.595, 0.971, 0.805],
}
FALLBACK_POOLED_J = [0.80, 0.62, 0.85, 0.76]
FALLBACK_TPR = [0.98, 0.98, 0.99, 0.99]
FALLBACK_TNR = [0.82, 0.64, 0.86, 0.78]


def metrics_from_dumps():
    """Recompute per-domain and pooled metrics from the raw dumps."""
    per = {d: [] for d in DOMAINS}
    pooled_rows = {r: [] for r in RUNGS}
    for d in DOMAINS:
        for r in RUNGS:
            rows = a.load_dump(d, r)
            pooled_rows[r].extend(rows)
            per[d].append(a.metrics(rows))
    pooled = [a.metrics(pooled_rows[r]) for r in RUNGS]
    return per, pooled


def metrics_from_cache():
    """Build the same per/pooled structures from the cached constants above."""
    per = {d: [{"youden_j": v} for v in FALLBACK_J[d]] for d in DOMAINS}
    pooled = [{"youden_j": FALLBACK_POOLED_J[i], "tpr": FALLBACK_TPR[i],
               "tnr": FALLBACK_TNR[i]} for i in range(4)]
    return per, pooled


def main():
    # Prefer recomputing from the raw dumps; fall back to the cached series when
    # the dumps are absent so the figure stays reproducible from the repo alone.
    try:
        per, pooled = metrics_from_dumps()
    except FileNotFoundError:
        print("note: bench-out/policy_length/ dumps not found — "
              "rendering from cached series in this script")
        per, pooled = metrics_from_cache()

    x = list(range(4))
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.2))

    # --- left: Youden's J per domain + pooled ---
    colors = {"marketing": "#4C72B0", "healthcare": "#C44E52",
              "code": "#55A868", "sql": "#8172B3"}
    for d in DOMAINS:
        axL.plot(x, [m["youden_j"] for m in per[d]], marker="o", ms=5,
                 lw=1.4, color=colors[d], alpha=0.85, label=d)
    axL.plot(x, [m["youden_j"] for m in pooled], marker="s", ms=8,
             lw=3.0, color="black", label="pooled", zorder=5)
    best = max(range(4), key=lambda i: pooled[i]["youden_j"])
    # Label the pooled peak from the empty pocket below-right of the marker so the
    # text clears the bunched domain lines that also peak at this rung.
    axL.annotate("sweet spot", xy=(best, pooled[best]["youden_j"]),
                 xytext=(best + 0.32, pooled[best]["youden_j"] - 0.20),
                 ha="left", fontsize=9,
                 arrowprops=dict(arrowstyle="->", lw=1))
    axL.set_xticks(x); axL.set_xticklabels(RUNG_LABELS, fontsize=8)
    axL.set_ylabel("Youden's J  (TPR + TNR − 1)")
    axL.set_title("(a) Policy length vs. firewall quality")
    axL.set_ylim(-0.05, 1.02)
    axL.grid(True, axis="y", alpha=0.3)
    # Lower-right pocket (below the healthcare line) is the only data-free area;
    # lower-center collides with the healthcare dip.
    axL.legend(fontsize=8, ncol=2, loc="lower right", framealpha=0.9)

    # --- right: pooled TPR vs TNR ---
    axR.plot(x, [m["tpr"] for m in pooled], marker="o", ms=6, lw=2.2,
             color="#1f77b4", label="TPR (attacks blocked)")
    axR.plot(x, [m["tnr"] for m in pooled], marker="o", ms=6, lw=2.2,
             color="#d62728", label="TNR (legit passed)")
    for i in x:
        axR.annotate(f"{pooled[i]['tpr']:.2f}", (i, pooled[i]["tpr"]),
                     textcoords="offset points", xytext=(0, 7), fontsize=7,
                     ha="center", color="#1f77b4")
        axR.annotate(f"{pooled[i]['tnr']:.2f}", (i, pooled[i]["tnr"]),
                     textcoords="offset points", xytext=(0, -12), fontsize=7,
                     ha="center", color="#d62728")
    axR.set_xticks(x); axR.set_xticklabels(RUNG_LABELS, fontsize=8)
    axR.set_ylabel("rate (pooled across domains)")
    axR.set_title("(b) Blocking is ~flat; over-refusal varies")
    axR.set_ylim(0.0, 1.05)
    axR.grid(True, axis="y", alpha=0.3)
    axR.legend(fontsize=8, loc="lower center")

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)
    # echo the numbers behind the figure for the caption
    print("pooled J:", [round(m["youden_j"], 3) for m in pooled])
    print("pooled TPR:", [round(m["tpr"], 3) for m in pooled])
    print("pooled TNR:", [round(m["tnr"], 3) for m in pooled])


if __name__ == "__main__":
    main()
