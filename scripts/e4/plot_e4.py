#!/usr/bin/env python3
"""E4 figure: harmful-action rate and benign-completion rate, guard OFF vs ON, with CIs.
-> paper/figs/agent_harm.png"""
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(BASE, "bench-out/e4/summary.json")))
OUT = os.path.join(BASE, "paper/figs/agent_harm.png")


def yerr(rates, cis):
    """matplotlib (2, n): row0 = lower errors, row1 = upper errors."""
    lower = [max(0.0, r - ci[0]) for r, ci in zip(rates, cis)]
    upper = [max(0.0, ci[1] - r) for r, ci in zip(rates, cis)]
    return [lower, upper]


def main():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10, 4.2))
    axA.bar([0, 1], [S["harm_off"], S["harm_on"]], color=["#C44E52", "#4C72B0"],
            yerr=yerr([S["harm_off"], S["harm_on"]], [S["harm_ci_off"], S["harm_ci_on"]]),
            capsize=5, width=0.6)
    axA.set_xticks([0, 1]); axA.set_xticklabels(["no firewall", "QFIRE"])
    axA.set_ylim(0, 1.05); axA.set_ylabel("harmful-action rate")
    axA.set_title(f"(a) Attack episodes: harm reached (n={S['n_attack']})")
    axA.grid(True, axis="y", alpha=0.3)
    for x, v in [(0, S["harm_off"]), (1, S["harm_on"])]:
        axA.text(x, v + 0.03, f"{v:.2f}", ha="center", fontsize=10)
    axB.bar([0, 1], [S["benign_off"], S["benign_on"]], color=["#999999", "#55A868"],
            yerr=yerr([S["benign_off"], S["benign_on"]], [S["benign_ci_off"], S["benign_ci_on"]]),
            capsize=5, width=0.6)
    axB.set_xticks([0, 1]); axB.set_xticklabels(["no firewall", "QFIRE"])
    axB.set_ylim(0, 1.05); axB.set_ylabel("benign-completion rate")
    axB.set_title(f"(b) Benign episodes: task completed (n={S['n_benign']})")
    axB.grid(True, axis="y", alpha=0.3)
    for x, v in [(0, S["benign_off"]), (1, S["benign_on"])]:
        axB.text(x, v + 0.03, f"{v:.2f}", ha="center", fontsize=10)
    fig.tight_layout(); os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170); print("wrote", OUT)


if __name__ == "__main__":
    main()
