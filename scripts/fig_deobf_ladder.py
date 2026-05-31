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

BASE = "/tmp/qfire-figures"
DATA = "/Users/jim/Desktop/qfire"
OUT = os.path.join(BASE, "paper/figs/deobf_ladder.png")

# chain -> normalization setting
SETTINGS = [("bench_hybrid", "off"), ("bench_hybrid_trig", "triggered"),
            ("bench_hybrid_norm", "always-on")]


def load(path):
    d = json.load(open(path))
    return {r["chain"]: r["overall"] for r in d["reports"]}


def main():
    clean = load(os.path.join(DATA, "bench-out/exp1/bench.json"))
    obf_m = load(os.path.join(DATA, "bench-out/exp2/bench.json"))
    obf_i = load(os.path.join(DATA, "bench-out/exp2_indep/bench.json"))

    x = np.arange(len(SETTINGS))
    rec_mirror = [obf_m[c]["recall"] for c, _ in SETTINGS]
    rec_indep = [obf_i[c]["recall"] for c, _ in SETTINGS]
    fpr_clean = [clean[c]["fpr"] for c, _ in SETTINGS]

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
    for xi, v in zip(x, fpr_clean):
        ax2.annotate(f"{v:.2f}", (xi, v), textcoords="offset points",
                     xytext=(0, -16), ha="center", color="#b91c1c", fontweight="bold")

    ax1.set_ylabel("Recall (obfuscated attacks caught)", color="#166534", fontsize=11)
    ax2.set_ylabel("FPR on clean traffic", color="#b91c1c", fontsize=11)
    ax1.set_ylim(0, 1.0)
    ax2.set_ylim(0, 0.35)
    ax1.set_xticks(x)
    ax1.set_xticklabels([s for _, s in SETTINGS], fontsize=12)
    ax1.set_xlabel("De-obfuscation normalization setting", fontsize=11)
    ax1.tick_params(axis="y", labelcolor="#166534")
    ax2.tick_params(axis="y", labelcolor="#b91c1c")

    # highlight the sweet spot
    ax1.axvspan(0.6, 1.4, color="#fef9c3", alpha=0.5, zorder=0)
    ax1.text(1.0, 0.06, "sweet spot:\nrecovers recall,\nFPR near baseline",
             ha="center", fontsize=9, color="#713f12", fontweight="bold")

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
