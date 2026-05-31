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

BASE = "/tmp/qfire-figures"
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
    data = json.load(open(COMBOS))
    fig, ax = plt.subplots(figsize=(8.2, 5.4))

    for d in data:
        single = d["k"] == 1
        color = "#2563eb" if single else "#16a34a"
        marker = "o" if single else "*"
        size = 130 if single else 200
        # tint the miscalibrated-included ensembles differently
        ax.scatter(d["lat"], d["f1"], s=size, marker=marker, color=color,
                   edgecolor="black", linewidth=0.6, zorder=3, alpha=0.9)

    # Pareto frontier
    front = pareto([(d["lat"], d["f1"], d["name"]) for d in data])
    fx = [p[0] for p in front]; fy = [p[1] for p in front]
    ax.plot(fx, fy, "--", color="#dc2626", lw=1.8, zorder=2, label="Pareto frontier")

    # annotate a few key points with non-overlapping placements
    by = {d["name"]: d for d in data}

    def note(name, dx, dy, text=None, color=None):
        d = by[name]
        ax.annotate(text or name, (d["lat"], d["f1"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=8.5, ha="left",
                    color=color or ("#166534" if d["k"] > 1 else "#1e3a8a"),
                    arrowprops=dict(arrowstyle="-", color="#9ca3af", lw=0.6))

    note("L3.1", 6, -36, "Llama 3.1 (best single:\nF1 0.995 @ 0.4 s)", "#1e3a8a")
    note("L3.2", 6, -4, "Llama 3.2 (over-blocks,\nFPR 0.28 alone)", "#1e3a8a")
    note("L3.1+L3.2+Q3", -150, -52,
         "L3.1+L3.2+Qwen3: F1 1.00\ndespite including\nmiscalibrated L3.2")

    ax.set_xscale("log")
    ax.set_xlabel("Latency p50 (s, log scale) — parallel cost = slowest judge", fontsize=11)
    ax.set_ylabel("F1", fontsize=11)
    ax.set_ylim(0.84, 1.025)
    ax.set_xlim(right=by["G4"]["lat"] * 1.7)
    ax.grid(alpha=0.25)
    # legend proxies
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2563eb",
               markeredgecolor="black", markersize=10, label="single judge"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#16a34a",
               markeredgecolor="black", markersize=15, label="k-of-n majority vote"),
        Line2D([0], [0], ls="--", color="#dc2626", label="Pareto frontier"),
    ], loc="lower right", fontsize=9)
    ax.set_title("Cost-accuracy frontier: voting reaches F1 1.00 but Llama 3.1 alone\n"
                 "gives 0.995 at 16x lower latency — voting buys robustness, not raw accuracy",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
