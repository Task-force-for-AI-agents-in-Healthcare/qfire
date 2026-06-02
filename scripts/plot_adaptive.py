#!/usr/bin/env python3
"""Grouped-bar recall figure for E1 from bench-out/adaptive/summary.json ->
paper/figs/adaptive_robustness.png. One group per adaptive set; bars =
DeBERTa, PromptGuard-2, QFIRE scope+PHI, PHI-only. Shows generic classifiers
collapsing under adaptive attack while QFIRE's positive-security scope+PHI holds.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/adaptive/summary.json")))
OUT = os.path.join(BASE, "paper/figs/adaptive_robustness.png")
SETS = ["impersonation_healthcare", "paraphrase_evaded", "encoded_healthcare", "encoded_injection"]
LABELS = ["scope-\nimpersonation\n(healthcare)", "paraphrase-\nto-evade", "encoded\n(healthcare)", "encoded\n(injection)"]
DETS = [("deberta", "DeBERTa", "#C44E52"),
        ("promptguard2", "PromptGuard-2", "#DD8452"),
        ("scope", "QFIRE scope+PHI", "#4C72B0"),
        ("phi", "QFIRE PHI-only", "#55A868")]


def main():
    sets = [s for s in SETS if s in S]
    w = 0.2
    fig, ax = plt.subplots(figsize=(12, 4.8))
    x = list(range(len(sets)))
    for di, (key, label, color) in enumerate(DETS):
        vals = [(S[s].get(key) or 0) for s in sets]
        bars = ax.bar([xi + di * w for xi in x], vals, width=w, label=label, color=color)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v*100:.0f}", (b.get_x() + b.get_width()/2, v), ha="center",
                        va="bottom", fontsize=7, color=color)
    ax.set_xticks([xi + 1.5 * w for xi in x])
    ax.set_xticklabels([LABELS[SETS.index(s)] for s in sets], fontsize=8)
    ax.set_ylabel("recall (fraction of adaptive attacks blocked)")
    ax.set_ylim(0, 1.08)
    ax.set_title("Recall under adaptive attack: generic classifiers collapse; QFIRE scope+PHI holds")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8, ncol=4, loc="lower center")
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
