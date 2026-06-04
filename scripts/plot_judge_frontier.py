#!/usr/bin/env python3
"""Memory-vs-J judge frontier figure -> paper/figs/judge_memory_frontier.png.

Reads bench-out/judge_frontier/results.json (from analyze_judge_frontier.py) and
plots, for each difficulty tier, Youden's J against measured peak VRAM (GB, log-x).
Each point is one (model, quant) config; the Pareto frontier (minimal memory for
maximal J) is drawn as a staircase and the saturation knee annotated — the
smallest judge that reaches within EPS of the tier's best J.

The two tiers tell the story: on T1 the frontier saturates at low memory (a tiny
edge proxy suffices); on T2 it pushes right (harder attacks need a bigger judge).

Usage: python3 scripts/plot_judge_frontier.py [results.json]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "bench-out/judge_frontier/results.json")
OUT = os.path.join(ROOT, "paper/figs/judge_memory_frontier.png")

# (key, legend label tied to the paper's benchmarks, color, marker). T1 is the
# QFIRE-HealthBench corpus (§7); T2 is the adaptive-attack family (§3.10,
# scope-impersonation + Base64-encoded exfiltration).
TIERS = [("t1", "Standard — QFIRE-HealthBench", "#4C72B0", "o"),
         ("t2", "Hard — adaptive (impersonation + encoded)", "#C44E52", "s")]


def main():
    if not os.path.exists(RESULTS):
        print(f"missing {RESULTS}; run analyze_judge_frontier.py first", file=sys.stderr)
        sys.exit(1)
    rows = json.load(open(RESULTS))

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for key, label, color, marker in TIERS:
        xs, ys = [], []
        for r in rows:
            tm = r["tiers"].get(key)
            vram = r["meta"].get("peak_vram_mb")
            if not tm or not vram:
                continue
            xs.append(vram / 1024.0)
            ys.append(tm["j"])
        if not xs:
            continue
        ax.scatter(xs, ys, c=color, marker=marker, s=75, zorder=3,
                   edgecolors="white", linewidths=0.8, label=label)

    # One compact params+quant label per config, hugging its T1 point. Quant tags
    # are shortened (Q4_K_M -> Q4). rotation_mode="anchor" keeps each label pinned
    # to its node; the labels lean up-and-right, except the rightmost which leans
    # up-and-left so it stays clear of the frame edge.
    def short_quant(q):
        return q.split("_")[0] if q else q
    labeled = sorted((r for r in rows if r["meta"].get("peak_vram_mb")),
                     key=lambda r: r["meta"]["peak_vram_mb"])
    n = len(labeled)
    prev_x, level = None, 0
    for i, r in enumerate(labeled):
        vram = r["meta"]["peak_vram_mb"] / 1024.0
        params = r["meta"].get("params_b")
        tm = r["tiers"].get("t1") or next(iter(r["tiers"].values()), None)
        if params is None or not tm:
            continue
        # Lift a label only when its neighbor is too close on the log axis, so the
        # tight 4-5 GB cluster never overlaps but isolated labels stay pinned low.
        level = (level ^ 1) if (prev_x and vram / prev_x < 1.22) else 0
        prev_x = vram
        last = i == n - 1
        ax.annotate(f"{params:g}B {short_quant(r['meta'].get('quant',''))}",
                    xy=(vram, tm["j"]),
                    xytext=(-4 if last else 4, 5 + level * 13), textcoords="offset points",
                    fontsize=7, color="#444",
                    ha="right" if last else "left", va="bottom",
                    rotation=22, rotation_mode="anchor")

    ax.set_xscale("log")
    ax.set_xlim(1.2, 22)            # pad so the 1.6 GB and 14.8 GB labels stay in-frame
    ax.set_ylim(-0.12, 1.18)        # headroom above J=1.0 so labels clear the title
    ax.set_xlabel("Judge model peak VRAM (GB, log scale)")
    ax.set_ylabel("Youden's J  (TPR − FPR)")
    ax.set_title("How small can the firewall judge be?  Memory vs. detection quality\n"
                 "Llama 3.1 / 3.2 judge, by parameter size and quantization",
                 fontsize=12, pad=10)
    ax.grid(True, which="both", axis="both", alpha=0.25)
    ax.legend(title="Attack benchmark", loc="lower right", framealpha=0.95, fontsize=8.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
