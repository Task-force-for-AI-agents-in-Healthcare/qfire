#!/usr/bin/env python3
"""E9 figure: per-pattern recall, full-transcript (QFIRE default) vs latest-turn-only,
from bench-out/multiturn/summary.json -> paper/figs/multiturn.png. Benign FPR annotated.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/multiturn/summary.json")))
OUT = os.path.join(BASE, "paper/figs/multiturn.png")

ORDER = ["split_payload", "context_priming", "crescendo"]
LABELS = {"split_payload": "split-payload", "context_priming": "context-priming",
          "crescendo": "crescendo"}


def main():
    fs.apply()
    pats = [p for p in ORDER if p in S]
    full = [S[p]["recall_full"] for p in pats]
    latest = [S[p]["recall_latest"] for p in pats]
    x = list(range(len(pats)))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    b1 = ax.bar([xi - w / 2 for xi in x], full, w, label="full transcript (QFIRE default)",
                color=fs.QFIRE, edgecolor=fs.QFIRE_DARK, linewidth=0.8)
    b2 = ax.bar([xi + w / 2 for xi in x], latest, w, label="latest turn only (naive)",
                color=fs.BAD, edgecolor="#8F2C20", linewidth=0.8)
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.2f}", (b.get_x() + b.get_width() / 2,
                        b.get_height()), ha="center", va="bottom", fontsize=12,
                        fontweight="bold", color=fs.INK)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[p] for p in pats])
    ax.set_ylabel("recall (fraction of multi-turn attacks blocked)")
    ax.set_ylim(0, 1.32)
    fpr_f = S.get("benign", {}).get("fpr_full")
    fpr_l = S.get("benign", {}).get("fpr_latest")
    ax.set_title("Multi-turn injection: full-transcript evaluation catches cross-turn "
                 f"buildup\n(benign FPR: full {fpr_f:.2f} / latest {fpr_l:.2f})")
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.legend(loc="upper center", ncol=2)
    fs.despine(ax)
    ax.grid(True, axis="y")
    ax.grid(False, axis="x")
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT)
    print("wrote", OUT)
    print("PLOT_MULTITURN_DONE")


if __name__ == "__main__":
    main()
