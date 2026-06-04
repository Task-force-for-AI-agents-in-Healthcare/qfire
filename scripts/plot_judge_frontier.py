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

TIERS = [("t1", "T1 standard", "#4C72B0", "o"),
         ("t2", "T2 hard", "#C44E52", "s")]
EPS = 0.02  # knee = smallest-memory config within EPS of the tier's max J


def pareto_upper_left(points):
    """Points (mem, j) on the min-memory / max-J frontier, sorted by memory."""
    pts = sorted(points, key=lambda p: (p[0], -p[1]))
    out, best_j = [], -1e9
    for mem, j, label in pts:
        if j > best_j + 1e-12:
            out.append((mem, j, label))
            best_j = j
    return out


def main():
    if not os.path.exists(RESULTS):
        print(f"missing {RESULTS}; run analyze_judge_frontier.py first", file=sys.stderr)
        sys.exit(1)
    rows = json.load(open(RESULTS))

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for key, label, color, marker in TIERS:
        pts = []
        for r in rows:
            tm = r["tiers"].get(key)
            vram = r["meta"].get("peak_vram_mb")
            if not tm or not vram:
                continue
            pts.append((vram / 1024.0, tm["j"], r["meta"].get("label", r["config"])))
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.scatter(xs, ys, c=color, marker=marker, s=70, zorder=3,
                   edgecolors="white", linewidths=0.8, label=label)

        front = pareto_upper_left(pts)
        if len(front) >= 2:
            fx = [p[0] for p in front]
            fy = [p[1] for p in front]
            ax.plot(fx, fy, color=color, lw=1.6, alpha=0.6, zorder=2,
                    drawstyle="steps-post")

        # Saturation knee: smallest-memory config within EPS of best J. Anchor
        # both annotations into the open lower band so neither hits the title.
        best_j = max(ys)
        knee = min((p for p in pts if p[1] >= best_j - EPS), key=lambda p: p[0])
        ytext = (0.42 if key == "t1" else 0.20)
        ax.annotate(f"{label} knee\nJ={knee[1]:.2f} @ {knee[0]:.1f} GB",
                    xy=(knee[0], knee[1]), xycoords="data",
                    xytext=(knee[0] * 1.15, ytext), textcoords="data",
                    fontsize=8, color=color, ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.0))

    # One compact params+quant label per config, anchored above its T1 point and
    # rotated so the dense 4-8 GB cluster stays legible. Quant tags are shortened
    # (Q4_K_M -> Q4) and the vertical offset alternates to avoid collisions.
    def short_quant(q):
        return q.split("_")[0] if q else q
    labeled = sorted((r for r in rows if r["meta"].get("peak_vram_mb")),
                     key=lambda r: r["meta"]["peak_vram_mb"])
    for i, r in enumerate(labeled):
        vram = r["meta"]["peak_vram_mb"]
        params = r["meta"].get("params_b")
        tm = r["tiers"].get("t1") or next(iter(r["tiers"].values()), None)
        if params is None or not tm:
            continue
        ax.annotate(f"{params:g}B {short_quant(r['meta'].get('quant',''))}",
                    xy=(vram / 1024.0, tm["j"]),
                    xytext=(0, 12 if i % 2 == 0 else 24), textcoords="offset points",
                    fontsize=7, color="#444", ha="center", va="bottom", rotation=30)

    ax.set_xscale("log")
    ax.set_xlabel("Judge model peak VRAM (GB, log scale)")
    ax.set_ylabel("Youden's J  (TPR − FPR)")
    ax.set_title("How small can the firewall judge be?\nMemory vs. detection quality (Llama judge, by size & quantization)",
                 pad=14)
    ax.grid(True, which="both", axis="both", alpha=0.25)
    ax.legend(title="Attack difficulty", loc="center right", framealpha=0.9)
    ax.set_ylim(min(-0.08, ax.get_ylim()[0]), 1.08)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
