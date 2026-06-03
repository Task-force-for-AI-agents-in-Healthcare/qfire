#!/usr/bin/env python3
"""Ensemble cost-accuracy frontier: every single judge and every k-of-n hard-vote
combination plotted in F1 x latency space, with the Pareto frontier drawn.

Honest framing: majority voting reaches the top F1 (1.00) but the best SINGLE
model (Llama 3.1) already attains 0.995 at 16x lower latency. Voting's real value
is robustness — the F1=1.00 ensembles INCLUDE the miscalibrated Llama 3.2
(FPR 0.28 alone), whose false positives get outvoted. So you can fold in a model
you don't fully trust without inheriting its failure mode, at a latency premium.

Latency for a combo = the slowest member (judges run concurrently).
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBOS = os.path.join(BASE, "bench-out/voting_combos.json")
OUT = os.path.join(BASE, "paper/figs/ensemble_frontier.png")


def pareto(points):
    """points: list of (lat, f1, name). Frontier = min latency for >= each F1
    (we want HIGH f1, LOW latency)."""
    pts = sorted(points, key=lambda p: (p[0], -p[1]))
    front = []
    best_f1 = -1
    for lat, f1, name in pts:
        if f1 > best_f1:
            front.append((lat, f1, name))
            best_f1 = f1
    return front


def main():
    fs.apply()
    data = json.load(open(COMBOS))
    fig, ax = plt.subplots(figsize=(8.4, 5.6))

    # ---- spread points that share an exact (lat, f1) so none hide ----------
    # group by coordinate, fan the cluster out symmetrically in log-x
    from collections import defaultdict
    groups = defaultdict(list)
    for d in data:
        groups[(d["lat"], d["f1"])].append(d)
    xpos = {}
    for (lat, f1), members in groups.items():
        n = len(members)
        # multiplicative jitter so it stays even on the log axis
        for i, d in enumerate(members):
            frac = (i - (n - 1) / 2) / max(n, 1)
            spread = 0.16 if n <= 2 else 0.26
            xpos[d["name"]] = lat * (1.0 + spread * frac)

    for d in data:
        single = d["k"] == 1
        x = xpos[d["name"]]
        if single:
            ax.scatter(x, d["f1"], s=150, marker="o", color=fs.QFIRE,
                       edgecolor="white", linewidth=1.1, zorder=4, alpha=0.95)
        else:
            ax.scatter(x, d["f1"], s=320, marker="*", color=fs.GOOD,
                       edgecolor="white", linewidth=1.0, zorder=4, alpha=0.95)

    # ---- Pareto frontier (use true coords, not jittered) -------------------
    front = pareto([(d["lat"], d["f1"], d["name"]) for d in data])
    fx = [p[0] for p in front]
    fy = [p[1] for p in front]
    ax.plot(fx, fy, "--", color=fs.BAD, lw=2.2, zorder=2)

    by = {d["name"]: d for d in data}

    # ---- annotate ONLY the two points that matter --------------------------
    # best single judge: Llama 3.1
    d = by["L3.1"]
    ax.annotate("Best single judge\nLlama 3.1 — F1 0.995 @ 0.4 s",
                (xpos["L3.1"], d["f1"]), textcoords="offset points",
                xytext=(14, -30), fontsize=12, ha="left", va="top",
                color=fs.QFIRE_DARK, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=fs.MUTED, lw=1.0,
                                shrinkA=0, shrinkB=4))

    # 3-model majority vote reaching F1 1.00
    d = by["L3.1+L3.2+G4"]
    ax.annotate("3-model majority vote\nF1 1.00 @ 7.2 s",
                (xpos["L3.1+L3.2+G4"], d["f1"]), textcoords="offset points",
                xytext=(-12, 24), fontsize=12, ha="right", va="bottom",
                color=fs.GOOD, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=fs.MUTED, lw=1.0,
                                shrinkA=0, shrinkB=4))

    ax.set_xscale("log")
    ax.set_xlabel("Latency p50 (s, log scale) — parallel cost = slowest judge")
    ax.set_ylabel("F1")
    ax.set_ylim(0.84, 1.03)
    ax.set_xlim(0.28, by["G4"]["lat"] * 2.0)
    fs.despine(ax)

    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor=fs.QFIRE,
               markeredgecolor="white", markersize=12, label="single judge"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor=fs.GOOD,
               markeredgecolor="white", markersize=18, label="k-of-n majority vote"),
        Line2D([0], [0], ls="--", color=fs.BAD, lw=2.2, label="Pareto frontier"),
    ], loc="lower right")

    ax.set_title("Voting buys robustness, not raw accuracy")
    fig.tight_layout()
    fig.savefig(OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
