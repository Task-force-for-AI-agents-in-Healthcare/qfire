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
        # scope-judge-only reference at Stage 2 (the robust component)
        sj = d.get("scope_judge_only_stage2")
        if sj is not None:
            ax.scatter([1], [sj], marker="*", s=240, color=fs.ACCENT,
                       edgecolor=fs.ACCENT_DK, linewidth=1.0, zorder=7)

    # compact inline annotation for the ★ markers (both sit near recall 1.0)
    ax.annotate("scope-judge only ≈ 1.0\n(robust component the\ncalibrated chain dilutes)",
                xy=(1, 1.0), xytext=(1.32, 0.78),
                fontsize=10.5, color=fs.ACCENT_DK, fontweight="bold",
                ha="left", va="center", linespacing=1.25,
                arrowprops=dict(arrowstyle="-", color=fs.ACCENT_DK, lw=1.0))

    ax.set_xticks(x)
    ax.set_xticklabels(XLAB)
    ax.set_xlim(-0.35, 2.55)
    ax.set_ylabel("recall (fraction of attacks blocked)")
    ax.set_ylim(0, 1.10)
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
