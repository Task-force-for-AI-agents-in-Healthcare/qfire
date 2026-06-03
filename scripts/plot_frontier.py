#!/usr/bin/env python3
"""Two-panel latency-vs-F1 frontier (public injection + QFIRE-HealthBench) ->
paper/figs/latency_f1_frontier.png. Reads the measured baseline JSONs for classifier
points; QFIRE's point is from the committed tables (paper/tables/{main,healthbench}.tex),
using the hybrid p95 (242 ms) as QFIRE's latency on both panels (HealthBench combined
short-circuits, so no separate p95 -- annotated in the caption). All numbers are measured.

To stay legible in the crowded classifier cluster, each baseline is a small numbered
marker keyed in a single legend below the panels (consistent numbering across panels);
QFIRE is a large blue star labelled in place. Each panel draws the Pareto frontier
(highest F1 reachable at or below a given latency) as a light dashed step and shades the
ideal corner. No two text labels can overlap because the only in-panel text is the tiny
numbers (auto-nudged) and the single QFIRE label.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from adjustText import adjust_text

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "paper/figs/latency_f1_frontier.png")

DOT = fs.BAD          # baseline detectors -- red dots
QCOL = fs.QFIRE       # QFIRE -- brand blue star

NAMES = {
    "deberta-70m-int8": "DeBERTa-70M (INT8)",
    "promptguard-2-22m": "PromptGuard-2 22M",
    "promptguard-2-86m": "PromptGuard-2 86M",
    "deberta-v3-injection": "DeBERTa-v3 (protectai)",
    "prompt-injection-sentinel": "Sentinel",
    "llm-judge-3.1-8b": "bare LLM-judge",
}
# stable numbering, ascending injection latency (fast -> slow)
ORDER = ["deberta-70m-int8", "promptguard-2-22m", "promptguard-2-86m",
         "deberta-v3-injection", "prompt-injection-sentinel", "llm-judge-3.1-8b"]
NUM = {k: i + 1 for i, k in enumerate(ORDER)}

QFIRE = {
    "injection": ("QFIRE hybrid", 242.26, 0.856),
    "healthbench": ("QFIRE combined", 242.26, 0.868),
}


def load(path):
    try:
        return json.load(open(os.path.join(BASE, path)))["results"]
    except Exception:
        return {}


def _pareto(points):
    best, front = None, []
    for lat, f1 in sorted(points, key=lambda p: (p[0], -p[1])):
        if best is None or f1 > best:
            front.append((lat, f1)); best = f1
    return front


def panel(ax, jsons, title, qfire, xlim, qfire_xytext, legend_loc):
    seen = {}
    for jp in jsons:
        for k, v in load(jp).items():
            if not isinstance(v, dict) or "f1" not in v:
                continue
            lat = (v.get("latency_ms") or {}).get("p95")
            if lat is None:
                continue
            seen[k] = (max(lat, 0.05), v["f1"])

    qlbl, qlat, qf1 = qfire
    all_pts = list(seen.values()) + [(qlat, qf1)]

    ax.set_xscale("log")
    ax.set_ylim(0.3, 1.0)
    ax.set_xlim(*xlim)
    # ideal-corner shading: high F1, low latency (top-left)
    ax.axvspan(xlim[0], qlat, ymin=(qf1 - 0.3) / 0.7, ymax=1.0,
               color=fs.QFIRE, alpha=0.07, zorder=0)
    ax.text(xlim[0] * 1.07, 0.985, "ideal: high F1, low latency",
            fontsize=9.5, style="italic", color=fs.MUTED, ha="left", va="top", zorder=1)

    # Pareto frontier as a light dashed step
    front = _pareto(all_pts)
    fx, fy, prev = [], [], None
    for lat, f1 in front:
        if prev is not None:
            fx += [prev[0], lat]; fy += [prev[1], prev[1]]
        fx.append(lat); fy.append(f1); prev = (lat, f1)
    fx.append(xlim[1]); fy.append(front[-1][1])
    ax.plot(fx, fy, ls="--", lw=1.5, color=fs.BASELINE_D, alpha=0.7, zorder=1,
            label="Pareto frontier (best F1 per latency)")

    # baseline detectors: small red dots with tiny numbered labels
    px, py, nums = [], [], []
    for k, (lat, f1) in seen.items():
        ax.scatter(lat, f1, s=52, color=DOT, edgecolor="white", linewidth=0.7, zorder=3)
        px.append(lat); py.append(f1)
        nums.append(ax.text(lat, f1, str(NUM[k]), fontsize=10.5, fontweight="bold",
                            color=fs.INK, ha="center", va="center", zorder=6))

    # QFIRE: large blue star with its label pinned in place
    ax.scatter(qlat, qf1, s=470, marker="*", color=QCOL,
               edgecolor="white", linewidth=1.3, zorder=5)
    qtext = ax.annotate(qlbl, xy=(qlat, qf1), xytext=qfire_xytext, textcoords="offset points",
                        fontsize=13, color=fs.QFIRE_DARK, fontweight="bold",
                        ha="center", va="bottom", zorder=8)
    px.append(qlat); py.append(qf1)

    # nudge only the tiny numbers apart (short faint leaders where needed)
    adjust_text(nums, x=px, y=py, ax=ax, objects=[qtext],
                arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5, shrinkA=1, shrinkB=2),
                expand=(1.6, 1.9), force_text=(0.5, 0.8), max_move=14,
                ensure_inside_axes=True)

    ax.set_xlabel("p95 latency (ms, log scale)")
    ax.set_ylabel("F1")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    fs.despine(ax)
    ax.legend(loc=legend_loc, fontsize=9.5, framealpha=0.95)


def main():
    fs.apply()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 6.3))
    panel(a1, ["bench-out/baselines.json", "bench-out/baselines_e3_injection.json",
               "bench-out/baselines_e10_injection.json"],
          "Public injection", QFIRE["injection"], (48, 2800),
          qfire_xytext=(2, 15), legend_loc="lower right")
    panel(a2, ["bench-out/baselines_healthbench.json",
               "bench-out/baselines_e3_healthbench.json",
               "bench-out/baselines_e10_healthbench.json"],
          "QFIRE-HealthBench", QFIRE["healthbench"], (35, 1300),
          qfire_xytext=(2, 15), legend_loc="lower right")
    fig.suptitle("Latency vs F1: fast classifiers are cheap but lose healthcare recall; "
                 "QFIRE holds at bounded latency", fontsize=15, fontweight="bold")

    # one numbered detector key below the panels (shared, two rows)
    row1 = ("$\\mathbf{1}$ DeBERTa-70M (INT8)      $\\mathbf{2}$ PromptGuard-2 22M"
            "      $\\mathbf{3}$ PromptGuard-2 86M")
    row2 = ("$\\mathbf{4}$ DeBERTa-v3 (protectai)      $\\mathbf{5}$ Sentinel"
            "      $\\mathbf{6}$ bare LLM-judge")
    fig.text(0.5, 0.058, row1, ha="center", va="bottom", fontsize=11, color=fs.INK)
    fig.text(0.5, 0.012, row2, ha="center", va="bottom", fontsize=11, color=fs.INK)

    fig.tight_layout(rect=(0, 0.10, 1, 0.95))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=230)
    print("wrote", OUT)
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
