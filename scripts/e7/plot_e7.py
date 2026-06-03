#!/usr/bin/env python3
"""E7 figure: attack-success rate guard OFF vs ON across the standard agent
benchmarks (AgentDojo per-suite + pooled, InjecAgent total) with the E4 mock-EHR
harmful-action rate for reference, plus a benign-utility panel.

-> paper/figs/agent_benchmarks.png

Reads bench-out/e7/summary.json (written by scripts/e7/analyze_e7.py).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # scripts/ dir
import figstyle as fs

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(BASE, "bench-out/e7/summary.json")))
OUT = os.path.join(BASE, "paper/figs/agent_benchmarks.png")


def yerr(rate, ci):
    if not ci:
        return (0.0, 0.0)
    return (max(0.0, rate - ci[0]), max(0.0, ci[1] - rate))


def collect():
    """Build ordered groups: (label, off_rate, off_ci, on_rate, on_ci, group) for the
    ATTACK-SUCCESS panel, and a parallel list for BENIGN-UTILITY. ``group`` tags the
    benchmark family so the panels can visually separate them."""
    asr_rows, util_rows = [], []
    ad = S.get("agentdojo", {})
    suites = sorted({su for g in ("off", "on") if g in ad for su in ad[g]["per_suite"]})
    for su in suites:
        off = ad.get("off", {}).get("per_suite", {}).get(su)
        on = ad.get("on", {}).get("per_suite", {}).get(su)
        if off and on:
            asr_rows.append((su, off["targeted_asr"], off["targeted_asr_ci"],
                             on["targeted_asr"], on["targeted_asr_ci"], "AgentDojo"))
            util_rows.append((su, off["benign_utility"], off["benign_utility_ci"],
                              on["benign_utility"], on["benign_utility_ci"], "AgentDojo"))
    # AgentDojo pooled
    if "off" in ad and "on" in ad:
        o, n = ad["off"]["pooled"], ad["on"]["pooled"]
        asr_rows.append(("AD pooled", o["targeted_asr"], o["targeted_asr_ci"],
                         n["targeted_asr"], n["targeted_asr_ci"], "AgentDojo"))
        util_rows.append(("AD pooled", o["benign_utility"], o["benign_utility_ci"],
                          n["benign_utility"], n["benign_utility_ci"], "AgentDojo"))
    # InjecAgent total (ASR-valid)
    ia = S.get("injecagent", {})
    if "off" in ia and "on" in ia:
        o, n = ia["off"]["total"], ia["on"]["total"]
        asr_rows.append(("InjecAgent", o["asr_valid"], o["asr_valid_ci"],
                         n["asr_valid"], n["asr_valid_ci"], "InjecAgent"))
    # E4 reference (harmful-action rate)
    e4 = S.get("e4_reference")
    if e4 and e4.get("harm_off") is not None:
        asr_rows.append(("E4 mock-EHR", e4["harm_off"], e4.get("harm_ci_off"),
                         e4["harm_on"], e4.get("harm_ci_on"), "E4 mock-EHR"))
    return asr_rows, util_rows


# minimum visible bar height (axes fraction of the 0..1.05 range) so a ~0 bar
# still reads as a drawn, contained bar rather than missing data.
MIN_BAR = 0.012


def _draw_bars(ax, xs, vals, errs, color, label, w):
    """Draw a bar series where ~0 values still render as a thin visible stub with
    the Wilson-CI whisker attached, plus a value label on near-zero bars."""
    heights = [max(v, MIN_BAR) for v in vals]
    bars = ax.bar(xs, heights, width=w, color=color, label=label,
                  edgecolor="white", linewidth=0.6, zorder=3)
    # error bars are drawn against the TRUE value, not the clamped stub height.
    ax.errorbar(xs, vals, yerr=errs, fmt="none", ecolor=fs.INK,
                elinewidth=1.3, capsize=4, capthick=1.3, zorder=4)
    return bars


def _grouped(ax, rows, ylabel, title, asr_panel):
    n = len(rows)
    w = 0.38
    off_v = [r[1] for r in rows]
    on_v = [r[3] for r in rows]
    off_e = list(zip(*[yerr(r[1], r[2]) for r in rows]))
    on_e = list(zip(*[yerr(r[3], r[4]) for r in rows]))
    off_e = [list(off_e[0]), list(off_e[1])] if off_e else [[], []]
    on_e = [list(on_e[0]), list(on_e[1])] if on_e else [[], []]

    # add a gap between consecutive benchmark families so AgentDojo is visually
    # set apart from InjecAgent / E4 mock-EHR.
    GAP = 0.8
    pos, boundaries, shift = [], [], 0.0
    for i, r in enumerate(rows):
        if i > 0 and r[5] != rows[i - 1][5]:
            boundaries.append(i + shift + GAP / 2 - 0.5)  # midpoint of the gap
            shift += GAP
        pos.append(i + shift)

    left = [p - w / 2 for p in pos]
    right = [p + w / 2 for p in pos]
    _draw_bars(ax, left, off_v, off_e, fs.BAD, "no firewall", w)
    _draw_bars(ax, right, on_v, on_e, fs.QFIRE, "QFIRE", w)

    # value labels on near-zero bars so they read as "contained", not missing.
    for p, v, e in zip(left, off_v, off_e[1]):
        if v < 0.05:
            ax.text(p, max(v, MIN_BAR) + e + 0.02, f"{v:.2f}", ha="center",
                    va="bottom", fontsize=10, fontweight="bold", color=fs.BAD)
    for p, v, e in zip(right, on_v, on_e[1]):
        if v < 0.05:
            ax.text(p, max(v, MIN_BAR) + e + 0.02, f"{v:.2f}", ha="center",
                    va="bottom", fontsize=10, fontweight="bold", color=fs.QFIRE_DARK)

    # family dividers + bracket labels
    ymax = 1.12
    for bx in boundaries:
        ax.plot([bx, bx], [0, 1.0], color=fs.MUTED, linestyle=(0, (4, 3)),
                linewidth=1.1, alpha=0.8, zorder=1)
    # group bracket labels along the top
    groups = []
    for i, r in enumerate(rows):
        if not groups or groups[-1][0] != r[5]:
            groups.append([r[5], i, i])
        else:
            groups[-1][2] = i
    # span a thin bracket line under each group label so families read clearly.
    yb = 1.045
    for gname, i0, i1 in groups:
        cx = (pos[i0] + pos[i1]) / 2
        x0, x1 = left[i0] - 0.05, right[i1] + 0.05
        ax.plot([x0, x1], [yb - 0.02, yb - 0.02], color=fs.MUTED,
                linewidth=1.4, alpha=0.85, clip_on=False, zorder=2)
        ax.text(cx, yb, gname, ha="center", va="bottom", fontsize=10.5,
                fontweight="bold", color=fs.MUTED)

    ax.set_xticks(pos)
    ax.set_xticklabels([r[0] for r in rows], rotation=25, ha="right", fontsize=12)
    ax.set_xlim(pos[0] - 0.7, pos[-1] + 0.7)
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.6)
    ax.grid(False, axis="x")
    fs.despine(ax)
    ax.legend(fontsize=12, loc="upper right",
              bbox_to_anchor=(1.0, 0.88))


def main():
    fs.apply()
    asr_rows, util_rows = collect()
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    _grouped(axA, asr_rows, "attack-success / harmful-action rate",
             "(a) Attack success — lower is better", asr_panel=True)
    _grouped(axB, util_rows, "benign utility (task solved)",
             "(b) Benign utility — higher is better", asr_panel=False)
    fig.suptitle("QFIRE on standard agent benchmarks (guard off vs on)",
                 fontsize=17, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print("wrote", OUT)
    print("E7_FIG_DONE")


if __name__ == "__main__":
    main()
