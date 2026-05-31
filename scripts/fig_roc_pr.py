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

BASE = "/tmp/qfire-figures"
DATA = "/Users/jim/Desktop/qfire"
DUMP = os.path.join(DATA, "bench-out/dump1")
OUT = os.path.join(BASE, "paper/figs/roc_pr.png")

CURVES = [
    ("bench_deberta", "DeBERTa-v3", "#2563eb"),
    ("bench_hybrid", "QFIRE hybrid", "#16a34a"),
    ("bench_aho", "Aho-Corasick", "#f59e0b"),
    ("bench_regex", "Regex denylist", "#a855f7"),
    ("bench_entropy", "Entropy", "#94a3b8"),
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
    fig, (axr, axp) = plt.subplots(1, 2, figsize=(10.5, 4.8))
    for chain, label, color in CURVES:
        try:
            y, s = load(chain)
        except FileNotFoundError:
            continue
        fpr, tpr = roc(y, s)
        a = auc(fpr, tpr)
        axr.plot(fpr, tpr, color=color, lw=2.2, label=f"{label} (AUC {a:.2f})")
        rec, prec = pr(y, s)
        axp.plot(rec, prec, color=color, lw=2.2, label=label)

    axr.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
    axr.set_xlabel("False-positive rate", fontsize=11)
    axr.set_ylabel("True-positive rate (recall)", fontsize=11)
    axr.set_title("ROC", fontsize=12, fontweight="bold")
    axr.legend(loc="lower right", fontsize=9)
    axr.set_xlim(0, 1); axr.set_ylim(0, 1.02)
    axr.grid(alpha=0.25)

    axp.set_xlabel("Recall", fontsize=11)
    axp.set_ylabel("Precision", fontsize=11)
    axp.set_title("Precision-Recall", fontsize=12, fontweight="bold")
    axp.legend(loc="lower left", fontsize=9)
    axp.set_xlim(0, 1); axp.set_ylim(0, 1.02)
    axp.grid(alpha=0.25)

    fig.suptitle("Learned detectors dominate lexical filters on the public corpus "
                 "(929 attacks / 1039 benign)", fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
    print("ROC_PR_DONE")


if __name__ == "__main__":
    main()
