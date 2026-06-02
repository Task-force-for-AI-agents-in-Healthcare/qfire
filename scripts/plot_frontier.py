#!/usr/bin/env python3
"""Two-panel latency-vs-F1 frontier (public injection + QFIRE-HealthBench) ->
paper/figs/latency_f1_frontier.png. Reads the measured baseline JSONs for classifier
points; QFIRE's point is from the committed tables (paper/tables/{main,healthbench}.tex),
using the hybrid p95 (242 ms) as QFIRE's latency on both panels (HealthBench combined
short-circuits, so no separate p95 — annotated in the caption). All numbers are measured.

The public-injection panel clusters five detectors into a tight latency/F1 band, so its
labels are placed by hand into the empty regions with thin leader lines; the HealthBench
panel is well spread and uses simple offset labels.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "paper/figs/latency_f1_frontier.png")

DOT = "#C44E52"
QCOL = "#4C72B0"

# Display names for the JSON result keys.
NAMES = {
    "deberta-v3-injection": "DeBERTa-v3 (protectai)",
    "promptguard-2-86m": "PromptGuard-2 86M",
    "promptguard-2-22m": "PromptGuard-2 22M",
    "prompt-injection-sentinel": "Sentinel",
    "llm-judge-3.1-8b": "bare LLM-judge",
    "deberta-70m-int8": "DeBERTa-70M (INT8)",
}
# QFIRE from committed tables; hybrid p95 used as latency proxy on both panels.
QFIRE = {
    "injection": ("QFIRE hybrid", 242.26, 0.856),
    "healthbench": ("QFIRE combined", 242.26, 0.868),
}

# Hand-tuned label anchors (in DATA coords) for the crowded public-injection panel.
# Each value is (label_x, label_y, ha, va); a thin leader line joins point -> label.
INJ_PLACE = {
    "PromptGuard-2 86M":       (150.0, 0.930, "right", "bottom"),
    "Sentinel":                (505.0, 0.965, "left",  "center"),
    "DeBERTa-v3 (protectai)":  (250.0, 0.700, "left",  "top"),
    "PromptGuard-2 22M":       (104.0, 0.605, "left",  "top"),
    "DeBERTa-70M (INT8)":      (138.0, 0.730, "left",  "center"),
    "bare LLM-judge":          (1450.0, 0.685, "right", "center"),
}
INJ_QFIRE_PLACE = (340.0, 0.828, "left", "center")


def load(path):
    try:
        return json.load(open(os.path.join(BASE, path)))["results"]
    except Exception:
        return {}


def _label(ax, name, lat, f1, place, color="black", fontsize=7, weight="normal"):
    """Place a label: leader-line callout if `place` is given, else a small offset."""
    if place is not None:
        lx, ly, ha, va = place
        ax.annotate(
            name, xy=(lat, f1), xytext=(lx, ly), textcoords="data",
            fontsize=fontsize, color=color, fontweight=weight, ha=ha, va=va, zorder=5,
            arrowprops=dict(arrowstyle="-", lw=0.6, color="0.55", shrinkA=0, shrinkB=2),
        )
    else:
        ax.annotate(name, (lat, f1), fontsize=fontsize, color=color, fontweight=weight,
                    xytext=(4, 3), textcoords="offset points", zorder=5)


def panel(ax, jsons, title, qfire, placements=None, qfire_place=None, xlim=None):
    placements = placements or {}
    seen = {}
    for jp in jsons:
        for k, v in load(jp).items():
            if not isinstance(v, dict) or "f1" not in v:
                continue
            lat = (v.get("latency_ms") or {}).get("p95")
            if lat is None:
                continue
            seen[k] = (max(lat, 0.05), v["f1"])  # later JSONs win (same key)
    for k, (lat, f1) in seen.items():
        name = NAMES.get(k, k)
        ax.scatter(lat, f1, s=45, color=DOT, zorder=3)
        _label(ax, name, lat, f1, placements.get(name))
    lbl, lat, f1 = qfire
    ax.scatter(lat, f1, s=160, marker="*", color=QCOL, zorder=4)
    _label(ax, lbl, lat, f1, qfire_place, color=QCOL, fontsize=8, weight="bold")
    ax.set_xscale("log")
    ax.set_xlabel("p95 latency (ms, log scale)")
    ax.set_ylabel("F1")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_ylim(0.3, 1.0)
    if xlim:
        ax.set_xlim(*xlim)


def main():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.3))
    panel(a1, ["bench-out/baselines.json", "bench-out/baselines_e3_injection.json",
               "bench-out/baselines_e10_injection.json"],
          "Public injection", QFIRE["injection"],
          placements=INJ_PLACE, qfire_place=INJ_QFIRE_PLACE, xlim=(70, 2800))
    panel(a2, ["bench-out/baselines_healthbench.json",
               "bench-out/baselines_e3_healthbench.json",
               "bench-out/baselines_e10_healthbench.json"],
          "QFIRE-HealthBench", QFIRE["healthbench"], xlim=(35, 1300))
    fig.suptitle("Latency vs F1: fast classifiers are cheap but lose healthcare recall; "
                 "QFIRE holds at bounded latency", fontsize=11)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
