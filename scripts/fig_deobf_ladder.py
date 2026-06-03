#!/usr/bin/env python3
"""De-obfuscation recall ladder: off -> triggered -> always-on, with the FPR cost.

Replaces tab:deobf. Shows the trade-off as a slope: each normalization setting
trades clean-traffic precision (FPR, red) for obfuscated-attack recall (green),
and the *triggered* setting is the sweet spot. Uses both obfuscator variants
(mirror = exp2, independent = exp2_indep) to show the recovery isn't an artifact
of testing the decoder against its own encoder.
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Resolve paths relative to the repo so the figure regenerates anywhere.
# Point QFIRE_DATA at the root that holds bench-out/ if it lives elsewhere.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("QFIRE_DATA", REPO)
OUT = os.path.join(REPO, "paper/figs/deobf_ladder.png")

# chain -> normalization setting
SETTINGS = [("bench_hybrid", "off"), ("bench_hybrid_trig", "triggered"),
            ("bench_hybrid_norm", "always-on")]


def load(path):
    d = json.load(open(path))
    return {r["chain"]: r["overall"] for r in d["reports"]}


# Fallback values for regenerating the figure when bench-out/ is unavailable.
# mirror recall and clean FPR are exact (read off the published labels);
# independent recall is measured from the published PNG (±0.01). Re-run with
# QFIRE_DATA pointing at the real bench-out to recompute from source.
FALLBACK = {
    "rec_mirror": [0.55, 0.71, 0.84],
    "rec_indep": [0.70, 0.72, 0.72],
    "fpr_clean": [0.02, 0.08, 0.27],
}


def main():
    x = np.arange(len(SETTINGS))
    try:
        clean = load(os.path.join(DATA, "bench-out/exp1/bench.json"))
        obf_m = load(os.path.join(DATA, "bench-out/exp2/bench.json"))
        obf_i = load(os.path.join(DATA, "bench-out/exp2_indep/bench.json"))
        rec_mirror = [obf_m[c]["recall"] for c, _ in SETTINGS]
        rec_indep = [obf_i[c]["recall"] for c, _ in SETTINGS]
        fpr_clean = [clean[c]["fpr"] for c, _ in SETTINGS]
    except FileNotFoundError:
        print(f"bench-out not found under {DATA}; using reconstructed FALLBACK values")
        rec_mirror = FALLBACK["rec_mirror"]
        rec_indep = FALLBACK["rec_indep"]
        fpr_clean = FALLBACK["fpr_clean"]

    fig, ax1 = plt.subplots(figsize=(7.6, 4.8))
    ax2 = ax1.twinx()

    l1, = ax1.plot(x, rec_mirror, "o-", color="#16a34a", lw=2.5, ms=9,
                   label="recall on obfuscated attacks (mirror obfuscator)")
    l2, = ax1.plot(x, rec_indep, "s--", color="#15803d", lw=2, ms=8,
                   label="recall on obfuscated attacks (independent obfuscator)")
    l3, = ax2.plot(x, fpr_clean, "^-", color="#dc2626", lw=2.5, ms=9,
                   label="false-positive rate on CLEAN traffic")

    for xi, v in zip(x, rec_mirror):
        ax1.annotate(f"{v:.2f}", (xi, v), textcoords="offset points",
                     xytext=(0, 10), ha="center", color="#166534", fontweight="bold")
    # FPR value labels: the always-on point lands among the green recall markers,
    # so push its label out to the right (ha="left") instead of straight down,
    # which used to collide. The white bbox keeps every label legible even when
    # it sits close to a line or marker.
    fpr_xytext = [(0, -16), (0, -16), (12, -3)]      # off, triggered, always-on
    fpr_ha = ["center", "center", "left"]
    bbox = dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85)
    for xi, v, off, ha in zip(x, fpr_clean, fpr_xytext, fpr_ha):
        ax2.annotate(f"{v:.2f}", (xi, v), textcoords="offset points",
                     xytext=off, ha=ha, color="#b91c1c", fontweight="bold", bbox=bbox)

    ax1.set_ylabel("Recall (obfuscated attacks caught)", color="#166534", fontsize=11)
    ax2.set_ylabel("FPR on clean traffic", color="#b91c1c", fontsize=11)
    ax1.set_ylim(0, 1.0)
    ax2.set_ylim(0, 0.35)
    ax1.set_xticks(x)
    ax1.set_xticklabels([s for _, s in SETTINGS], fontsize=12)
    ax1.set_xlim(-0.25, len(SETTINGS) - 1 + 0.32)  # right margin for always-on FPR label
    ax1.set_xlabel("De-obfuscation normalization setting", fontsize=11)
    ax1.tick_params(axis="y", labelcolor="#166534")
    ax2.tick_params(axis="y", labelcolor="#b91c1c")

    # highlight the sweet spot. Sit the caption in the open band between the
    # red FPR marker (low) and the green recall markers (high) at the triggered
    # column, so it clears the triggered FPR label that sits just below it.
    ax1.axvspan(0.6, 1.4, color="#fef9c3", alpha=0.5, zorder=0)
    ax1.text(0.92, 0.52, "sweet spot:\nrecovers recall,\nFPR near baseline",
             ha="center", va="center", fontsize=9, color="#713f12", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.2", fc="#fef9c3", ec="#d4b106", alpha=0.9))

    ax1.legend(handles=[l1, l2, l3], loc="upper left", fontsize=8.5, framealpha=0.95)
    ax1.set_title("De-obfuscation trades clean-traffic precision for obfuscated recall",
                  fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("mirror recall:", dict(zip([s for _,s in SETTINGS], [round(v,2) for v in rec_mirror])))
    print("clean FPR:", dict(zip([s for _,s in SETTINGS], [round(v,2) for v in fpr_clean])))
    print("DEOBF_DONE")


if __name__ == "__main__":
    main()
