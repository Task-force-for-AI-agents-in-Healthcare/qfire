#!/usr/bin/env python3
"""HERO figure (Fig 1): the paper's punchline in one glance.

Two panels, the SAME three detectors on each:
  left  = generic injection (public corpus)  -> all ~tied at the top
  right = healthcare (QFIRE-HealthBench)      -> SOTA collapses, QFIRE holds

The visual drop between panels IS the thesis. Numbers are read from the committed
bench JSON; only presentation lives here.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
DATA = BASE
OUT = os.path.join(BASE, "paper/figs/hero_recall_gap.png")


def public_recall():
    b = json.load(open(os.path.join(DATA, "bench-out/baselines.json")))["results"]
    pg2 = b["promptguard-2-86m"]["recall"]
    deb = b["deberta-v3-injection"]["recall"]
    e1 = json.load(open(os.path.join(DATA, "bench-out/exp1/bench.json")))
    qf = [r for r in e1["reports"] if r["chain"] == "bench_hybrid"][0]["overall"]["recall"]
    return {"PromptGuard-2": pg2, "DeBERTa-v3": deb, "QFIRE": qf}


def health_recall():
    hb = json.load(open(os.path.join(DATA, "bench-out/baselines_healthbench.json")))["results"]
    pg2 = hb["promptguard-2-86m"]["recall"]
    deb = hb["deberta-v3-injection"]["recall"]
    h = json.load(open(os.path.join(DATA, "bench-out/healthbench/bench.json")))
    qf = [r for r in h["reports"] if r["chain"] == "bench_combined"][0]["overall"]["recall"]
    return {"PromptGuard-2": pg2, "DeBERTa-v3": deb, "QFIRE": qf}


def main():
    fs.apply()
    pub = public_recall()
    hea = health_recall()
    labels = ["PromptGuard-2", "DeBERTa-v3", "QFIRE"]
    colors = [fs.BASELINE, fs.BASELINE, fs.QFIRE]

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.9), sharey=True)
    for ax, data, title in [
        (axes[0], pub, "Generic injection\n(public corpus, 929 attacks)"),
        (axes[1], hea, "Healthcare threats\n(QFIRE-HealthBench, 1000 attacks)"),
    ]:
        vals = [data[l] for l in labels]
        x = np.arange(len(labels))
        bars = ax.bar(x, vals, color=colors, width=0.62,
                      edgecolor=fs.INK, linewidth=1.0, zorder=3)
        bars[2].set_edgecolor(fs.QFIRE_DARK); bars[2].set_linewidth(1.7)
        for b, v, l in zip(bars, vals, labels):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=15, fontweight="bold",
                    color=(fs.QFIRE_DARK if l == "QFIRE" else fs.INK))
        ax.set_title(title, fontsize=14.5, color=fs.INK)
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=12.5, rotation=12)
        ax.set_ylim(0, 1.14); ax.set_yticks(np.arange(0, 1.01, 0.2))
        fs.despine(ax)
        ax.grid(axis="y", alpha=0.7); ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Recall (attacks caught)", fontsize=13.5)

    # right panel: vertical pure-red collapse arrow (ends just above the centred
    # "0.40" label so it clears it) + white "QFIRE holds" inside the blue bar
    axR = axes[1]
    RED = "#C00000"
    drop_from, drop_to = pub["PromptGuard-2"], hea["PromptGuard-2"]
    axR.annotate("", xy=(0, drop_to + 0.09), xytext=(0, 0.91),
                 arrowprops=dict(arrowstyle="-|>", color=RED, lw=2.8))
    axR.text(0.13, 0.71, f"SOTA collapses\n{drop_from:.2f} → {drop_to:.2f}",
             color=RED, fontsize=12.5, fontweight="bold", ha="left", va="center")
    axR.text(2, hea["QFIRE"] - 0.20, "QFIRE\nholds", color="white",
             fontsize=12.5, fontweight="bold", ha="center", va="center")

    fig.suptitle("The same detectors: tied on generic injection, far apart on healthcare",
                 fontsize=16, fontweight="bold", y=1.04, color=fs.INK)
    fig.tight_layout()
    fig.savefig(OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("public:", {k: round(v, 3) for k, v in pub.items()})
    print("health:", {k: round(v, 3) for k, v in hea.items()})
    print("HERO_DONE")


if __name__ == "__main__":
    main()
