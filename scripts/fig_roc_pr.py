#!/usr/bin/env python3
"""ROC + precision-recall curves for the detectors on the public corpus.

Replaces the detail of tab:main with two curve panels computed from the
per-prompt score dumps (bench-out/dump1/*.jsonl). Shows visually why the learned
detectors (DeBERTa, hybrid) dominate the lexical ones, and reports AUC in-legend.
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = BASE
DUMP = os.path.join(DATA, "bench-out/dump1")
OUT = os.path.join(BASE, "paper/figs/roc_pr.png")

# (chain, label, color, lw, zorder) — QFIRE blue + thick + on top; DeBERTa a
# distinct secondary (amber); the lexical filters recede in muted grey.
CURVES = [
    ("bench_hybrid",  "QFIRE hybrid",   fs.QFIRE,    3.2, 6),
    ("bench_deberta", "DeBERTa-v3",     fs.ACCENT_DK, 2.4, 5),
    # lexical filters: neutral greys/black so they recede behind the coloured
    # learned detectors (QFIRE blue, DeBERTa amber) but stay distinguishable.
    ("bench_aho",     "Aho-Corasick",   "#555555",    1.7, 3),   # dark gray
    ("bench_regex",   "Regex denylist", "#AEAEAE",    1.7, 2),   # light gray
    ("bench_entropy", "Entropy",        "#111111",    1.7, 2),   # black
]


def load(chain):
    rows = [json.loads(l) for l in open(os.path.join(DUMP, chain + ".jsonl")) if l.strip()]
    y = np.array([1 if r["is_attack"] else 0 for r in rows])
    s = np.array([r["score"] for r in rows], dtype=float)
    return y, s


def roc(y, s):
    thr = np.unique(np.concatenate([[1e9], s, [-1e9]]))[::-1]
    P = y.sum(); N = len(y) - P
    tpr, fpr = [], []
    for t in thr:
        pred = s >= t
        tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0))
        tpr.append(tp / P if P else 0); fpr.append(fp / N if N else 0)
    return np.array(fpr), np.array(tpr)


def pr(y, s):
    thr = np.unique(s)[::-1]
    prec, rec = [], []
    P = y.sum()
    for t in thr:
        pred = s >= t
        tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0))
        prec.append(tp / (tp + fp) if tp + fp else 1.0)
        rec.append(tp / P if P else 0)
    return np.array(rec), np.array(prec)


def auc(x, yv):
    o = np.argsort(x)
    return float(np.trapz(yv[o], x[o]))


def main():
    fs.apply()
    fig, (axr, axp) = plt.subplots(1, 2, figsize=(11, 4.8))
    aucs = {}
    for chain, label, color, lw, zo in CURVES:
        try:
            y, s = load(chain)
        except FileNotFoundError:
            continue
        fpr, tpr = roc(y, s)
        a = auc(fpr, tpr)
        aucs[label] = a
        axr.plot(fpr, tpr, color=color, lw=lw, zorder=zo,
                 label=f"{label} (AUC {a:.2f})", solid_capstyle="round")
        rec, prec = pr(y, s)
        ap = auc(rec, prec)
        axp.plot(rec, prec, color=color, lw=lw, zorder=zo,
                 label=f"{label} (AP {ap:.2f})", solid_capstyle="round")

    axr.plot([0, 1], [0, 1], "--", color=fs.MUTED, lw=1, alpha=0.6, zorder=1)
    axr.set_xlabel("False-positive rate")
    axr.set_ylabel("True-positive rate (recall)")
    axr.set_title("ROC")
    # ROC curves hug the top-left, so park the legend in the empty lower-right.
    axr.legend(loc="lower right", fontsize=11)
    axr.set_xlim(0, 1); axr.set_ylim(0, 1.02)
    fs.despine(axr)

    axp.set_xlabel("Recall")
    axp.set_ylabel("Precision")
    axp.set_title("Precision-Recall")
    # PR curves hug the top, so the lower-left corner is clear for the legend.
    axp.legend(loc="lower left", fontsize=11)
    axp.set_xlim(0, 1); axp.set_ylim(0, 1.02)
    fs.despine(axp)

    fig.suptitle("Learned detectors dominate lexical filters on the public corpus "
                 "(929 attacks / 1039 benign)", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("AUCs:", aucs)
    print("ROC_PR_DONE")


if __name__ == "__main__":
    main()
