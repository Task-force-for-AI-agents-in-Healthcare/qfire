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

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/cascade/summary.json")))
OUT = os.path.join(BASE, "paper/figs/cascade.png")

STAGES = ["recall_stage1", "recall_stage2", "recall_stage3"]
XLAB = ["Stage 1\nstandard", "Stage 2\ndefense-aware", "Stage 3\nadaptive (in-loop)"]
COL = {"healthcare": "#4C72B0", "injection": "#C44E52"}


def main():
    fig, ax = plt.subplots(figsize=(8, 5))
    x = list(range(3))
    for dom, d in S.items():
        ys = [d[s] for s in STAGES]
        ax.plot(x, ys, "-o", color=COL.get(dom, "#555"), lw=2, label=f"QFIRE — {dom}")
        for xi, y in zip(x, ys):
            ax.annotate(f"{y:.2f}", (xi, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=9, color=COL.get(dom, "#555"))
        # scope-judge-only reference at Stage 2
        sj = d.get("scope_judge_only_stage2")
        if sj is not None:
            ax.scatter([1], [sj], marker="*", s=130, color=COL.get(dom, "#555"),
                       edgecolor="k", zorder=5)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(XLAB)
    ax.set_ylabel("recall (fraction of attacks blocked)")
    ax.set_ylim(0, 1.08)
    ax.set_title("Cascade adaptive attack: recall collapses under in-the-loop paraphrase\n"
                 "(★ = scope-judge-only on Stage-2 — the robust component the calibrated chain dilutes)")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)
    print("PLOT_CASCADE_DONE")


if __name__ == "__main__":
    main()
