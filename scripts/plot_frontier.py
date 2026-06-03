#!/usr/bin/env python3
"""Two-panel latency-vs-F1 frontier (public injection + QFIRE-HealthBench) ->
paper/figs/latency_f1_frontier.png. Reads the measured baseline JSONs for classifier
points; QFIRE's point is from the committed tables (paper/tables/{main,healthbench}.tex),
using the hybrid p95 (242 ms) as QFIRE's latency on both panels (HealthBench combined
short-circuits, so no separate p95 — annotated in the caption). All numbers are measured.

Each panel draws the Pareto frontier (highest F1 reachable at or below a given latency)
as a light dashed step and shades the ideal corner (high F1, low latency), so QFIRE's
position on the bounded-latency frontier reads at a glance. QFIRE is a large blue star;
baseline detectors are smaller red dots. Labels sit adjacent to their points with small
offsets (and short leaders only where the cluster is tight).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import figstyle as fs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "paper/figs/latency_f1_frontier.png")

DOT = fs.BAD          # baseline detectors — red dots
QCOL = fs.QFIRE       # QFIRE — brand blue star

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

# Per-point label placement for the crowded public-injection panel. The points
# form two tight clusters (~106-113 ms and ~197-242 ms), so the cluster labels get
# leader lines that fan them out into the empty lower region; no two labels overlap.
# (dx_pts, dy_pts, ha, va, leader)  -- offset in POINTS from the marker.
INJ_PLACE = {
    "DeBERTa-70M (INT8)":      (-16, -30, "right",  "top",    True),
    "PromptGuard-2 22M":       (  2, -64, "center", "top",    True),
    "PromptGuard-2 86M":       (-34,  22, "right",  "bottom", True),
    "DeBERTa-v3 (protectai)":  ( 40, -34, "left",   "top",    True),
    "Sentinel":                ( 11,  -3, "left",   "center", False),
    "bare LLM-judge":          (  0, -20, "center", "top",    False),
}
INJ_QFIRE_PLACE = (34, 10, "left", "bottom")
# HealthBench panel is well spread: simple per-point offsets (a couple get leaders).
HB_PLACE = {
    "DeBERTa-70M (INT8)":      (-10, 12, "right", "bottom", True),
    "PromptGuard-2 22M":       (8,  -8, "left",  "top",    False),
    "PromptGuard-2 86M":       (10,  4, "left",  "bottom", False),
    "DeBERTa-v3 (protectai)":  (8,  13, "left",  "bottom", True),
    "Sentinel":                (8, -12, "left",  "top",    False),
    "bare LLM-judge":          (-9,  7, "right", "bottom", False),
}
HB_QFIRE_PLACE = (-13, 8, "right", "bottom")


def load(path):
    try:
        return json.load(open(os.path.join(BASE, path)))["results"]
    except Exception:
        return {}


def _label(ax, name, lat, f1, place, color=fs.INK, fontsize=11, weight="normal"):
    """Place a label at a small point-offset from the marker (short leader optional)."""
    dx, dy, ha, va, leader = place
    arrow = (dict(arrowstyle="-", lw=0.6, color="0.6", shrinkA=0, shrinkB=2)
             if leader else None)
    ax.annotate(name, xy=(lat, f1), xytext=(dx, dy), textcoords="offset points",
                fontsize=fontsize, color=color, fontweight=weight,
                ha=ha, va=va, zorder=6, arrowprops=arrow)


def _pareto(points):
    """Non-dominated set: lowest latency wins; F1 must strictly improve to keep a point."""
    best = None
    front = []
    for lat, f1 in sorted(points, key=lambda p: (p[0], -p[1])):
        if best is None or f1 > best:
            front.append((lat, f1))
            best = f1
    return front


def panel(ax, jsons, title, qfire, placements, qfire_place, xlim):
    seen = {}
    for jp in jsons:
        for k, v in load(jp).items():
            if not isinstance(v, dict) or "f1" not in v:
                continue
            lat = (v.get("latency_ms") or {}).get("p95")
            if lat is None:
                continue
            seen[k] = (max(lat, 0.05), v["f1"])  # later JSONs win (same key)

    qlbl, qlat, qf1 = qfire
    all_pts = list(seen.values()) + [(qlat, qf1)]

    # --- ideal-corner shading: high F1, low latency (top-left) -----------------
    ax.set_xscale("log")
    ax.set_ylim(0.3, 1.0)
    ax.set_xlim(*xlim)
    # shade the top-left "ideal" box: F1 >= QFIRE's F1 and latency <= QFIRE's.
    ax.axvspan(xlim[0], qlat, ymin=(qf1 - 0.3) / 0.7, ymax=1.0,
               color=fs.QFIRE, alpha=0.07, zorder=0)
    ax.text(xlim[0] * 1.07, 0.985, "ideal: high F1, low latency",
            fontsize=9.5, style="italic", color=fs.MUTED, ha="left", va="top", zorder=1)

    # --- Pareto frontier as a light dashed step --------------------------------
    front = _pareto(all_pts)
    fx, fy = [], []
    prev = None
    for lat, f1 in front:
        if prev is not None:
            fx += [prev[0], lat]   # horizontal hold then step up
            fy += [prev[1], prev[1]]
        fx.append(lat)
        fy.append(f1)
        prev = (lat, f1)
    # extend last segment to the right edge so the frontier spans the axes
    fx.append(xlim[1])
    fy.append(front[-1][1])
    ax.plot(fx, fy, ls="--", lw=1.6, color=fs.BASELINE_D, alpha=0.7, zorder=1,
            label="Pareto frontier (optimal: best F1 per latency)")

    # --- baseline detectors: small red dots ------------------------------------
    for k, (lat, f1) in seen.items():
        name = NAMES.get(k, k)
        ax.scatter(lat, f1, s=58, color=DOT, edgecolor="white", linewidth=0.8, zorder=3)
        _label(ax, name, lat, f1, placements[name])

    # --- QFIRE: large blue star ------------------------------------------------
    ax.scatter(qlat, qf1, s=420, marker="*", color=QCOL,
               edgecolor="white", linewidth=1.2, zorder=5)
    _label(ax, qlbl, qlat, qf1, (*qfire_place, False),
           color=fs.QFIRE_DARK, fontsize=12.5, weight="bold")

    ax.set_xlabel("p95 latency (ms, log scale)")
    ax.set_ylabel("F1")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.35)
    fs.despine(ax)
    ax.legend(loc="lower right", fontsize=10)


def main():
    fs.apply()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.6))
    panel(a1, ["bench-out/baselines.json", "bench-out/baselines_e3_injection.json",
               "bench-out/baselines_e10_injection.json"],
          "Public injection", QFIRE["injection"],
          INJ_PLACE, INJ_QFIRE_PLACE, xlim=(48, 2800))
    panel(a2, ["bench-out/baselines_healthbench.json",
               "bench-out/baselines_e3_healthbench.json",
               "bench-out/baselines_e10_healthbench.json"],
          "QFIRE-HealthBench", QFIRE["healthbench"],
          HB_PLACE, HB_QFIRE_PLACE, xlim=(35, 1300))
    fig.suptitle("Latency vs F1: fast classifiers are cheap but lose healthcare recall; "
                 "QFIRE holds at bounded latency", fontsize=14.5, y=1.0)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=230)
    print("wrote", OUT)
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
