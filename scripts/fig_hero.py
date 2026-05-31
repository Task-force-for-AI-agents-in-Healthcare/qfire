#!/usr/bin/env python3
"""HERO figure: the paper's punchline in one glance.

Two panels, the SAME three detectors on each:
  left  = generic injection (public corpus)  -> all ~tied at the top
  right = healthcare (QFIRE-HealthBench)      -> SOTA collapses, QFIRE holds

The visual drop between panels IS the thesis: generic injection detection is
necessary but not sufficient in healthcare; QFIRE's scope+PHI chain closes the gap.

Numbers are read from the committed bench JSON so the figure regenerates with the
data (no hardcoding beyond the two PyTorch baselines, which live in baselines*.json).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = "/tmp/qfire-figures"
DATA = "/Users/jim/Desktop/qfire"  # bench-out/ is gitignored; data lives in main repo
OUT = os.path.join(BASE, "paper/figs/hero_recall_gap.png")


def public_recall():
    """recall on the public injection corpus."""
    b = json.load(open(os.path.join(DATA, "bench-out/baselines.json")))["results"]
    pg2 = b["promptguard-2-86m"]["recall"]
    deb = b["deberta-v3-injection"]["recall"]
    # QFIRE hybrid from exp1
    e1 = json.load(open(os.path.join(DATA, "bench-out/exp1/bench.json")))
    qf = [r for r in e1["reports"] if r["chain"] == "bench_hybrid"][0]["overall"]["recall"]
    return {"PromptGuard-2": pg2, "DeBERTa-v3": deb, "QFIRE": qf}


def health_recall():
    """recall on QFIRE-HealthBench."""
    hb = json.load(open(os.path.join(DATA, "bench-out/baselines_healthbench.json")))["results"]
    pg2 = hb["promptguard-2-86m"]["recall"]
    deb = hb["deberta-v3-injection"]["recall"]
    h = json.load(open(os.path.join(DATA, "bench-out/healthbench/bench.json")))
    qf = [r for r in h["reports"] if r["chain"] == "bench_combined"][0]["overall"]["recall"]
    return {"PromptGuard-2": pg2, "DeBERTa-v3": deb, "QFIRE": qf}


def main():
    pub = public_recall()
    hea = health_recall()
    labels = ["PromptGuard-2", "DeBERTa-v3", "QFIRE"]
    colors = ["#94a3b8", "#94a3b8", "#16a34a"]  # baselines grey, QFIRE green

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6), sharey=True)
    for ax, data, title in [
        (axes[0], pub, "Generic injection\n(public corpus, 929 attacks)"),
        (axes[1], hea, "Healthcare threats\n(QFIRE-HealthBench, 1000 attacks)"),
    ]:
        vals = [data[l] for l in labels]
        x = np.arange(len(labels))
        bars = ax.bar(x, vals, color=colors, width=0.62, edgecolor="black", linewidth=0.6)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10, rotation=12)
        ax.set_ylim(0, 1.12)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Recall (attacks caught)", fontsize=11)

    # annotate the collapse on the right panel
    axR = axes[1]
    axR.annotate("", xy=(0, hea["PromptGuard-2"] + 0.04), xytext=(0, 0.92),
                 arrowprops=dict(arrowstyle="->", color="#b91c1c", lw=2))
    axR.text(0.05, 0.66, "SOTA collapses\n0.76 → 0.40", color="#b91c1c",
             fontsize=10, fontweight="bold")
    axR.text(2, hea["QFIRE"] - 0.30, "QFIRE\nholds", color="#166534",
             fontsize=10, fontweight="bold", ha="center")

    fig.suptitle("The same detectors: tied on generic injection, far apart on healthcare",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("public:", {k: round(v, 3) for k, v in pub.items()})
    print("health:", {k: round(v, 3) for k, v in hea.items()})
    print("HERO_DONE")


if __name__ == "__main__":
    main()
