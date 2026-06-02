#!/usr/bin/env python3
"""E5 figure: (a) in-dist vs held-out recall bars (DeBERTa vs QFIRE) and (b) a
DeBERTa-score calibration curve (FPR vs threshold) with the calibrated point and the
held-out realized FPR marked. -> paper/figs/external_validity.png
"""
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "bench-out/external")
S = json.load(open(os.path.join(ROOT, "summary.json")))
OUT = os.path.join(BASE, "paper/figs/external_validity.png")


def overall(run):
    p = os.path.join(ROOT, run, "bench.json")
    return json.load(open(p))["reports"][0]["overall"] if os.path.exists(p) else {}


def main():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.2))
    # (a) recall transfer
    groups = ["in-dist", "held-out"]
    deb = [overall("indist").get("recall", 0), overall("heldout").get("recall", 0)]
    qf = [overall("qfire_indist").get("recall", 0), overall("qfire_heldout").get("recall", 0)]
    x = range(len(groups))
    axA.bar([i-0.2 for i in x], deb, width=0.4, label="DeBERTa", color="#C44E52")
    axA.bar([i+0.2 for i in x], qf, width=0.4, label="QFIRE (default)", color="#4C72B0")
    axA.set_xticks(list(x)); axA.set_xticklabels(groups); axA.set_ylabel("recall")
    axA.set_ylim(0, 1.05); axA.set_title("(a) Transfer: recall in-dist vs held-out")
    axA.grid(True, axis="y", alpha=0.3); axA.legend(fontsize=8)
    # (b) calibration curve: FPR vs threshold on in-dist + held-out benign, for the
    # QFIRE *chain* score (the deployed operating point — it spreads across [0,1], unlike
    # the DeBERTa probability which clusters near 0 on benign). Calibrate t on in-dist for
    # the target FPR, show the realized FPR on held-out at that fixed t.
    bi, bh, t = S["chain_benign_indist"], S["chain_benign_heldout"], S["chain_calib_t"]
    ts = [i/100 for i in range(0, 101)]
    fpr_i = [sum(1 for s in bi if s >= th)/len(bi) for th in ts]
    fpr_h = [sum(1 for s in bh if s >= th)/len(bh) for th in ts]
    axB.plot(ts, fpr_i, color="#4C72B0", label="in-dist benign")
    axB.plot(ts, fpr_h, color="#55A868", label="held-out benign")
    if t is not None:
        realized = sum(1 for s in bh if s >= t)/len(bh) if bh else 0.0
        axB.axvline(t, ls="--", color="grey", lw=1)
        axB.annotate(f"calibrated t={t:.2f}", xy=(t, 0.55), fontsize=8, rotation=90,
                     va="center", color="grey")
        axB.plot([t], [realized], "o", color="#55A868", ms=7, zorder=5)
        axB.annotate(f"held-out FPR={realized:.2f}", xy=(t, realized), xytext=(t+0.06, realized+0.05),
                     fontsize=8, color="#2f6b46")
    axB.axhline(S["target_fpr"], ls=":", color="grey", lw=1)
    axB.annotate(f"target FPR={S['target_fpr']:.2f}", xy=(0.62, S["target_fpr"]),
                 xytext=(0.62, S["target_fpr"]+0.04), fontsize=8, color="grey")
    axB.set_xlabel("QFIRE chain-score threshold"); axB.set_ylabel("FPR (benign blocked)")
    axB.set_ylim(0, 1.02)
    axB.set_title("(b) Threshold transfer (calibrated on in-dist)")
    axB.grid(True, alpha=0.3); axB.legend(fontsize=8, loc="upper right")
    fig.tight_layout(); os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170); print("wrote", OUT)


if __name__ == "__main__":
    main()
