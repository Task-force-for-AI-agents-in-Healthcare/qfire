#!/usr/bin/env python3
"""Two-panel latency-vs-F1 frontier (public injection + QFIRE-HealthBench) ->
paper/figs/latency_f1_frontier.png. Reads the measured baseline JSONs for classifier
points; QFIRE's point is from the committed tables (paper/tables/{main,healthbench}.tex),
using the hybrid p95 (242 ms) as QFIRE's latency on both panels (HealthBench combined
short-circuits, so no separate p95 — annotated in the caption). All numbers are measured.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "paper/figs/latency_f1_frontier.png")

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


def load(path):
    try:
        return json.load(open(os.path.join(BASE, path)))["results"]
    except Exception:
        return {}


def panel(ax, jsons, title, qfire):
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
        ax.scatter(lat, f1, s=45, color="#C44E52", zorder=3)
        ax.annotate(NAMES.get(k, k), (lat, f1), fontsize=7,
                    xytext=(4, 3), textcoords="offset points")
    lbl, lat, f1 = qfire
    ax.scatter(lat, f1, s=140, marker="*", color="#4C72B0", zorder=4)
    ax.annotate(lbl, (lat, f1), fontsize=8, color="#4C72B0", fontweight="bold",
                xytext=(4, -10), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_xlabel("p95 latency (ms, log scale)")
    ax.set_ylabel("F1")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_ylim(0.3, 1.0)


def main():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
    panel(a1, ["bench-out/baselines.json", "bench-out/baselines_e3_injection.json",
               "bench-out/baselines_e10_injection.json"],
          "Public injection", QFIRE["injection"])
    panel(a2, ["bench-out/baselines_healthbench.json",
               "bench-out/baselines_e3_healthbench.json",
               "bench-out/baselines_e10_healthbench.json"],
          "QFIRE-HealthBench", QFIRE["healthbench"])
    fig.suptitle("Latency vs F1: fast classifiers are cheap but lose healthcare recall; "
                 "QFIRE holds at bounded latency", fontsize=11)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)
    print("FRONTIER_DONE")


if __name__ == "__main__":
    main()
