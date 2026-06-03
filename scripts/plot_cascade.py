#!/usr/bin/env python3
"""E8 figure: staged recall (Stage 1 standard -> Stage 2 defense-aware -> Stage 3 adaptive
in-the-loop) per domain, from bench-out/cascade/summary.json -> paper/figs/cascade.png.
Annotates the scope-judge-only Stage-2 recall (the robust component).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/cascade/summary.json")))
OUT = os.path.join(BASE, "paper/figs/cascade.png")

STAGES = ["recall_stage1", "recall_stage2", "recall_stage3"]
XLAB = ["Stage 1\nstandard", "Stage 2\ndefense-aware", "Stage 3\nadaptive (in-loop)"]
COL = {"healthcare": fs.QFIRE, "injection": fs.BAD}


def main():
    fs.apply()
    fig, ax = plt.subplots(figsize=(8, 5))
    x = list(range(3))
    for dom, d in S.items():
        col = COL.get(dom, fs.MUTED)
        ys = [d[s] for s in STAGES]
        ax.plot(x, ys, "-o", color=col, lw=2.6, markersize=9,
                markeredgecolor="white", markeredgewidth=1.1,
                label=f"QFIRE — {dom}", zorder=4)
        for xi, y in zip(x, ys):
            ax.annotate(f"{y:.2f}", (xi, y), textcoords="offset points",
                        xytext=(0, 10), ha="center", fontsize=12,
                        fontweight="bold", color=col, zorder=6)
        # scope-judge-only reference at Stage 2: colour-code each star to MATCH
        # its line (blue = healthcare, red = injection) and nudge the two apart in
        # x so they don't overlap; label each with its value.
        sj = d.get("scope_judge_only_stage2")
        if sj is not None:
            sx = 1 + (-0.14 if dom == "healthcare" else 0.14)
            ax.scatter([sx], [sj], marker="*", s=330, color=col,
                       edgecolor="black", linewidth=1.2, zorder=7)
            ax.annotate(f"{sj:.2f}", (sx, sj), textcoords="offset points",
                        xytext=(0, 12), ha="center", fontsize=11,
                        fontweight="bold", color=col, zorder=8)

    # inline annotation: the ★ markers are the per-domain scope-judge-only recall
    ax.annotate("★ = scope-judge only at Stage 2\n(matches its line colour) — the robust\ncomponent the calibrated chain dilutes",
                xy=(1.14, 0.97), xytext=(1.40, 0.74),
                fontsize=10, color=fs.INK, fontweight="bold",
                ha="left", va="center", linespacing=1.3,
                arrowprops=dict(arrowstyle="-", color=fs.MUTED, lw=1.0))

    ax.set_xticks(x)
    ax.set_xticklabels(XLAB)
    ax.set_xlim(-0.35, 2.55)
    ax.set_ylabel("recall (fraction of attacks blocked)")
    ax.set_ylim(0, 1.15)
    ax.set_title("Recall collapses under the in-the-loop paraphrase attacker")
    ax.legend(loc="lower left", fontsize=12)
    ax.grid(True, axis="y")
    fs.despine(ax)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT)
    print("wrote", OUT)
    print("PLOT_CASCADE_DONE")


if __name__ == "__main__":
    main()
