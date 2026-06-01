#!/usr/bin/env python3
"""3-panel E2 figure from bench-out/throughput/summary.json ->
paper/figs/throughput_scaling.png:
(a) latency vs #rules (wall parallel vs summed serial, log-log),
(b) QPS + tail latency vs in-flight concurrency,
(c) short-circuit expensive-node work saved (bar).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(BASE, "bench-out/throughput/summary.json")))
OUT = os.path.join(BASE, "paper/figs/throughput_scaling.png")


def main():
    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(15, 4.2))

    # (a) latency vs #rules at engine-concurrency 16 (parallel) vs 1 (serial)
    A = S["A"]

    def series(ec):
        pts = sorted((int(k.split("_")[0]), v) for k, v in A.items()
                     if k.endswith(f"_{ec}"))
        return ([k for k, _ in pts],
                [v["wall"] for _, v in pts],
                [v["summed"] for _, v in pts])

    ks, wall16, summed16 = series(16)
    axA.plot(ks, summed16, marker="s", lw=2, color="#C44E52",
             label="summed (serial-equiv)")
    axA.plot(ks, wall16, marker="o", lw=2, color="#4C72B0",
             label="wall (parallel, ec=16)")
    axA.set_xscale("log", base=2)
    axA.set_xlabel("# rules in chain"); axA.set_ylabel("ms / prompt")
    axA.set_title("(a) Latency vs rule count")
    axA.grid(True, which="both", alpha=0.3); axA.legend(fontsize=8)

    # (b) QPS (left axis) + p99 tail latency (right axis) vs concurrency
    B = S["B"]
    ns = sorted(int(n) for n in B)
    qps = [B[str(n)]["qps"] for n in ns]
    p99 = [B[str(n)]["p99"] for n in ns]
    axB.plot(ns, qps, marker="o", lw=2, color="#55A868", label="throughput (QPS)")
    axB.set_xscale("log", base=2)
    axB.set_xlabel("in-flight concurrency N")
    axB.set_ylabel("throughput (prompts/s)", color="#55A868")
    axB.set_ylim(0, max(qps) * 1.4)
    axB.set_title("(b) Throughput flat; tail latency grows")
    axB.grid(True, which="both", alpha=0.3)
    axBr = axB.twinx()
    axBr.plot(ns, p99, marker="^", lw=2, color="#C44E52", label="p99 latency (ms)")
    axBr.set_ylabel("p99 latency (ms)", color="#C44E52")
    axBr.set_yscale("log")
    lines = axB.get_lines() + axBr.get_lines()
    axB.legend(lines, [l.get_label() for l in lines], fontsize=8, loc="center left")

    # (c) short-circuit: detector work/prompt, gated vs always
    C = S["C"]
    axC.bar(["always-run", "gated"],
            [C["always_detector_ms"], C["gated_detector_ms"]],
            color=["#C44E52", "#4C72B0"])
    axC.set_ylabel("detector work (ms / prompt)")
    axC.set_title(f"(c) Short-circuit saves {C['pct_saved']:.0f}% work")
    axC.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
