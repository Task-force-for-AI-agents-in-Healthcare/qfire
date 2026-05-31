#!/usr/bin/env python3
"""Two related figures for the judge-model story:

(A) judge_bars.png  — per-model F1 / FPR / latency (single judge), replacing
    tab:judgeabl. Bars make the L3.2 over-block and the latency spread obvious.

(B) ensemble_tradeoff.png — accuracy vs latency scatter: each single judge as a
    point, plus the 3-model hard-majority ENSEMBLE, on F1 x latency axes. Shows the
    voting scheme's accuracy/latency trade-off (the parallel cost = slowest judge).

Reads single-judge results from the merged judge_abl_judge_scope dir and the new
ensemble + qwen3:8b-solo runs from the worktree bench-out.
"""
import glob
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = "/tmp/qfire-figures"
DATA = "/Users/jim/Desktop/qfire"
ABL = os.path.join(DATA, "bench-out/judge_abl_judge_scope")
WT = os.path.join(BASE, "bench-out")

# single judges: (result dir, dump dir, label, p50 latency seconds)
SINGLES = [
    (os.path.join(ABL, "llama3_1_8b"), os.path.join(ABL, "dump_llama3_1_8b"), "Llama 3.1 8B", 0.4),
    (os.path.join(ABL, "llama3_2_latest"), os.path.join(ABL, "dump_llama3_2_latest"), "Llama 3.2", 0.6),
    (os.path.join(ABL, "gemma4_latest"), os.path.join(ABL, "dump_gemma4_latest"), "Gemma 4", 7.2),
    (os.path.join(WT, "judge_solo_qwen3_8b"), os.path.join(WT, "dump_solo_qwen3_8b"), "Qwen3 8B", None),
]
ENSEMBLE = (os.path.join(WT, "ensemble"), os.path.join(WT, "ensemble_dump"),
            "3-model vote\n(L3.1+G4+Qwen3)")


def overall(d):
    j = json.load(open(os.path.join(d, "bench.json")))
    return j["reports"][0]["overall"]


def p50_seconds(result_dir, fallback):
    try:
        o = overall(result_dir)
        v = o.get("p50_ms")
        if v:
            return v / 1000.0
    except Exception:
        pass
    return fallback


def fig_bars(rows):
    labels = [r["label"] for r in rows]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, key, title, color in [
        (axes[0], "f1", "F1", "#2563eb"),
        (axes[1], "fpr", "False-positive rate", "#dc2626"),
        (axes[2], "p50", "Latency p50 (s, log)", "#7c3aed"),
    ]:
        vals = [r[key] for r in rows]
        bars = ax.bar(x, vals, color=color, width=0.6, edgecolor="black", linewidth=0.5)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, (f"{v:.2f}" if key != "p50" else f"{v:.1f}s"),
                    ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5, rotation=20)
        ax.spines[["top", "right"]].set_visible(False)
        if key == "p50":
            ax.set_yscale("log")
        else:
            ax.set_ylim(0, 1.1)
    fig.suptitle("Judge-model ablation: the backend model changes accuracy and latency",
                 fontsize=12, fontweight="bold", y=1.03)
    fig.tight_layout()
    out = os.path.join(BASE, "paper/figs/judge_bars.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def fig_tradeoff(rows, ens):
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    for r in rows:
        ax.scatter(r["p50"], r["f1"], s=140, color="#2563eb", zorder=3, edgecolor="black")
        ax.annotate(r["label"], (r["p50"], r["f1"]), textcoords="offset points",
                    xytext=(8, 6), fontsize=9)
    if ens:
        ax.scatter(ens["p50"], ens["f1"], s=260, marker="*", color="#16a34a",
                   zorder=4, edgecolor="black", label="3-model majority vote")
        ax.annotate(ens["label"], (ens["p50"], ens["f1"]), textcoords="offset points",
                    xytext=(10, -22), fontsize=9, color="#166534", fontweight="bold")
    ax.set_xscale("log")
    ax.set_xlabel("Judge latency p50 (s, log scale)", fontsize=11)
    ax.set_ylabel("F1", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.set_title("Accuracy vs. latency: single judges vs. a 3-model majority vote",
                 fontsize=12, fontweight="bold")
    if ens:
        ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    out = os.path.join(BASE, "paper/figs/ensemble_tradeoff.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def main():
    rows = []
    for rdir, ddir, label, fb in SINGLES:
        if not os.path.exists(os.path.join(rdir, "bench.json")):
            print("skip (pending):", label)
            continue
        o = overall(rdir)
        rows.append({"label": label, "f1": o["f1"], "fpr": o["fpr"],
                     "p50": p50_seconds(rdir, fb if fb else 6.6)})
    ens = None
    if os.path.exists(os.path.join(ENSEMBLE[0], "bench.json")):
        o = overall(ENSEMBLE[0])
        ens = {"label": ENSEMBLE[2], "f1": o["f1"], "fpr": o["fpr"],
               "p50": p50_seconds(ENSEMBLE[0], None)}
        print("ensemble:", {k: round(v, 3) if isinstance(v, float) else v for k, v in ens.items()})
    fig_bars(rows)
    fig_tradeoff(rows, ens)
    print("singles:", [(r["label"], round(r["f1"], 3), round(r["p50"], 2)) for r in rows])
    print("JUDGE_FIGS_DONE")


if __name__ == "__main__":
    main()
