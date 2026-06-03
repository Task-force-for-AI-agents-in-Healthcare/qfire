#!/usr/bin/env python3
"""E7 figure: attack-success rate guard OFF vs ON across the standard agent
benchmarks (AgentDojo per-suite + pooled, InjecAgent total) with the E4 mock-EHR
harmful-action rate for reference, plus a benign-utility panel.

-> paper/figs/agent_benchmarks.png

Reads bench-out/e7/summary.json (written by scripts/e7/analyze_e7.py).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(BASE, "bench-out/e7/summary.json")))
OUT = os.path.join(BASE, "paper/figs/agent_benchmarks.png")

OFF_C, ON_C = "#C44E52", "#4C72B0"  # red = no firewall, blue = QFIRE


def yerr(rate, ci):
    if not ci:
        return (0.0, 0.0)
    return (max(0.0, rate - ci[0]), max(0.0, ci[1] - rate))


def collect():
    """Build ordered groups: (label, off_rate, off_ci, on_rate, on_ci) for the
    ATTACK-SUCCESS panel, and a parallel list for BENIGN-UTILITY."""
    asr_rows, util_rows = [], []
    ad = S.get("agentdojo", {})
    suites = sorted({su for g in ("off", "on") if g in ad for su in ad[g]["per_suite"]})
    for su in suites:
        off = ad.get("off", {}).get("per_suite", {}).get(su)
        on = ad.get("on", {}).get("per_suite", {}).get(su)
        if off and on:
            asr_rows.append((su, off["targeted_asr"], off["targeted_asr_ci"],
                             on["targeted_asr"], on["targeted_asr_ci"]))
            util_rows.append((su, off["benign_utility"], off["benign_utility_ci"],
                              on["benign_utility"], on["benign_utility_ci"]))
    # AgentDojo pooled
    if "off" in ad and "on" in ad:
        o, n = ad["off"]["pooled"], ad["on"]["pooled"]
        asr_rows.append(("AD pooled", o["targeted_asr"], o["targeted_asr_ci"],
                         n["targeted_asr"], n["targeted_asr_ci"]))
        util_rows.append(("AD pooled", o["benign_utility"], o["benign_utility_ci"],
                          n["benign_utility"], n["benign_utility_ci"]))
    # InjecAgent total (ASR-valid)
    ia = S.get("injecagent", {})
    if "off" in ia and "on" in ia:
        o, n = ia["off"]["total"], ia["on"]["total"]
        asr_rows.append(("InjecAgent", o["asr_valid"], o["asr_valid_ci"],
                         n["asr_valid"], n["asr_valid_ci"]))
    # E4 reference (harmful-action rate)
    e4 = S.get("e4_reference")
    if e4 and e4.get("harm_off") is not None:
        asr_rows.append(("E4 mock-EHR", e4["harm_off"], e4.get("harm_ci_off"),
                         e4["harm_on"], e4.get("harm_ci_on")))
    return asr_rows, util_rows


def _grouped(ax, rows, ylabel, title):
    n = len(rows)
    xs = range(n)
    w = 0.38
    off_v = [r[1] for r in rows]
    on_v = [r[3] for r in rows]
    off_e = list(zip(*[yerr(r[1], r[2]) for r in rows])) or [(), ()]
    on_e = list(zip(*[yerr(r[3], r[4]) for r in rows])) or [(), ()]
    ax.bar([x - w / 2 for x in xs], off_v, width=w, color=OFF_C, label="no firewall",
           yerr=[list(off_e[0]), list(off_e[1])], capsize=3)
    ax.bar([x + w / 2 for x in xs], on_v, width=w, color=ON_C, label="QFIRE",
           yerr=[list(on_e[0]), list(on_e[1])], capsize=3)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([r[0] for r in rows], rotation=25, ha="right", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=9)


def main():
    asr_rows, util_rows = collect()
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(12, 4.6))
    _grouped(axA, asr_rows, "attack-success / harmful-action rate",
             "(a) Attack success — lower is better")
    _grouped(axB, util_rows, "benign utility (task solved)",
             "(b) Benign utility — higher is better")
    fig.suptitle("QFIRE on standard agent benchmarks (guard off vs on)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print("wrote", OUT)
    print("E7_FIG_DONE")


if __name__ == "__main__":
    main()
