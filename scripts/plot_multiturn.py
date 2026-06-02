#!/usr/bin/env python3
"""E9 figure: per-pattern recall, full-transcript (QFIRE default) vs latest-turn-only,
from bench-out/multiturn/summary.json -> paper/figs/multiturn.png. Benign FPR annotated.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/multiturn/summary.json")))
OUT = os.path.join(BASE, "paper/figs/multiturn.png")

ORDER = ["split_payload", "context_priming", "crescendo"]
LABELS = {"split_payload": "split-payload", "context_priming": "context-priming",
          "crescendo": "crescendo"}


def main():
    pats = [p for p in ORDER if p in S]
    full = [S[p]["recall_full"] for p in pats]
    latest = [S[p]["recall_latest"] for p in pats]
    x = list(range(len(pats)))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.8))
    b1 = ax.bar([xi - w / 2 for xi in x], full, w, label="full transcript (QFIRE default)",
                color="#4C72B0")
    b2 = ax.bar([xi + w / 2 for xi in x], latest, w, label="latest turn only (naive)",
                color="#C44E52")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height()*100:.0f}", (b.get_x() + b.get_width() / 2,
                        b.get_height()), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[p] for p in pats])
    ax.set_ylabel("recall (fraction of multi-turn attacks blocked)")
    ax.set_ylim(0, 1.1)
    fpr_f = S.get("benign", {}).get("fpr_full")
    fpr_l = S.get("benign", {}).get("fpr_latest")
    ax.set_title("Multi-turn injection: full-transcript evaluation catches cross-turn "
                 f"buildup\n(benign FPR: full {fpr_f:.2f} / latest {fpr_l:.2f})")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)
    print("PLOT_MULTITURN_DONE")


if __name__ == "__main__":
    main()
