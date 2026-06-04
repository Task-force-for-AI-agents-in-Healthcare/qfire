#!/usr/bin/env python3
"""Build the detector x threat-category recall heatmap for the paper.

Reads the per-prompt bench dumps (bench-out/hb_dump/<chain>.jsonl, attacks first
in dataset order) and the labeled HealthBench dataset, and renders a heatmap of
per-category recall for each detector chain to paper/figs/heatmap.png.

This visualizes which filter catches which healthcare threat class — and where the
single-classifier chains have zero coverage that the PHI/scope rules fill.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.path.join(BASE, "bench-out/hb_dump")
DS = os.path.join(BASE, "corpora/healthcare_bench/dataset.jsonl")
OUT = os.path.join(BASE, "paper/figs/heatmap.png")

# chain dump -> display column label
CHAINS = [
    ("bench_deberta", "DeBERTa\n(injection)"),
    ("bench_phi", "PHI\ndetector"),
    ("bench_hybrid", "hybrid\n(lex +\nDeBERTa)"),
    ("bench_combined", "combined\n(inj + PHI\n+ scope)"),
]

CAT_ORDER = [
    "direct_injection", "system_exfil", "jailbreak", "phi_exfil",
    "phi_smuggle", "cross_patient", "bulk_export", "reidentification",
    "clinical_advice",
]
CAT_LABEL = {
    "direct_injection": "direct injection",
    "system_exfil": "system-prompt exfil",
    "jailbreak": "jailbreak",
    "phi_exfil": "PHI exfiltration",
    "phi_smuggle": "PHI smuggling",
    "cross_patient": "cross-patient access",
    "bulk_export": "bulk export",
    "reidentification": "re-identification",
    "clinical_advice": "out-of-scope advice",
}


def main():
    cats = []
    for line in open(DS):
        o = json.loads(line)
        if o["label"] == "malicious":
            cats.append(o["category"])
    n = len(cats)

    blocked = {}
    for dump, _ in CHAINS:
        p = os.path.join(DUMP, dump + ".jsonl")
        rows = [json.loads(l) for l in open(p) if l.strip()][:n]
        blocked[dump] = [bool(r["blocked"]) for r in rows]

    present = [c for c in CAT_ORDER if c in set(cats)]
    M = np.zeros((len(present), len(CHAINS)))
    counts = {}
    for i, cat in enumerate(present):
        idx = [k for k in range(n) if cats[k] == cat]
        counts[cat] = len(idx)
        for j, (dump, _) in enumerate(CHAINS):
            b = blocked[dump]
            M[i, j] = sum(1 for k in idx if b[k]) / max(len(idx), 1)

    fs.apply()

    combined_j = len(CHAINS) - 1  # rightmost "combined" column — the punchline

    fig, ax = plt.subplots(figsize=(12.5, 10.0))
    im = ax.imshow(M, cmap=fs.HEAT_CMAP, vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_xticks(range(len(CHAINS)))
    ax.set_xticklabels([lbl for _, lbl in CHAINS], fontsize=15)
    # emphasize the combined column header
    for j, tick in enumerate(ax.get_xticklabels()):
        if j == combined_j:
            tick.set_fontweight("bold")
            tick.set_color("black")
            tick.set_fontsize(16)
    ax.set_yticks(range(len(present)))
    ax.set_yticklabels([f"{CAT_LABEL[c]}  (n={counts[c]})" for c in present], fontsize=15)

    for i in range(len(present)):
        for j in range(len(CHAINS)):
            v = M[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="black" if 0.25 < v < 0.85 else "white",
                    fontsize=18,
                    fontweight="bold" if j == combined_j else "normal")

    ax.set_title("Per-category recall by detector chain\n(QFIRE-HealthBench, 1000 malicious prompts)",
                 fontsize=19, pad=16)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("recall (fraction blocked)", fontsize=15)
    cbar.ax.tick_params(labelsize=12)
    # thin black borders on every cell (improves readability); no centre gridlines
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, len(CHAINS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(present), 1), minor=True)
    ax.grid(which="minor", color="black", linewidth=0.7)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_visible(True); spine.set_color("black"); spine.set_linewidth(0.7)

    # bold border around the rightmost "combined" column — the all-green punchline
    rect = Rectangle((combined_j - 0.5, -0.5), 1, len(present),
                     fill=False, edgecolor="black", linewidth=4.5,
                     zorder=5, clip_on=False)
    ax.add_patch(rect)

    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("HEATMAP_DONE")


if __name__ == "__main__":
    main()
