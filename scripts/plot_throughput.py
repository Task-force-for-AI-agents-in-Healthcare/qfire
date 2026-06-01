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


def _series(group, ec):
    pts = sorted((int(k.split("_")[0]), v) for k, v in group.items()
                 if k.endswith(f"_{ec}"))
    return ([k for k, _ in pts],
            [v["wall"] for _, v in pts],
            [v["summed"] for _, v in pts])


def main():
    fig, ((axA, axAio), (axB, axC)) = plt.subplots(2, 2, figsize=(12, 8.4))

    # (a) CPU-bound fan-out: wall ~= summed (no speedup) at ec=16
    ks, wall16, summed16 = _series(S["A"], 16)
    axA.plot(ks, summed16, marker="s", lw=2, color="#C44E52", label="summed (serial-equiv)")
    axA.plot(ks, wall16, marker="o", lw=2, color="#4C72B0", label="wall (parallel, ec=16)")
    axA.set_xscale("log", base=2)
    axA.set_xlabel("# rules in chain"); axA.set_ylabel("ms / prompt")
    axA.set_title("(a) CPU-bound (deberta): fan-out gives no speedup")
    axA.grid(True, which="both", alpha=0.3); axA.legend(fontsize=8)

    # (a-IO) I/O-bound judge fan-out: wall << summed (real parallel speedup)
    AIO = S.get("A_IO", {})
    if AIO:
        ks2, wall2, summed2 = _series(AIO, 16)
        axAio.plot(ks2, summed2, marker="s", lw=2, color="#C44E52", label="summed (serial-equiv)")
        axAio.plot(ks2, wall2, marker="o", lw=2, color="#55A868", label="wall (parallel, ec=16)")
        if ks2:
            sp = summed2[-1] / wall2[-1] if wall2[-1] else 0
            axAio.annotate(f"{sp:.1f}x", xy=(ks2[-1], wall2[-1]),
                           xytext=(ks2[-1] * 0.5, wall2[-1] + (summed2[-1] - wall2[-1]) * 0.4),
                           fontsize=10, arrowprops=dict(arrowstyle="->", lw=1))
        axAio.set_xscale("log", base=2)
        axAio.set_xlabel("# judge (I/O) nodes in chain"); axAio.set_ylabel("ms / prompt")
        axAio.set_title("(b) I/O-bound (judge): fan-out overlaps the wait")
        axAio.grid(True, which="both", alpha=0.3); axAio.legend(fontsize=8)

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
    axB.set_title("(c) Throughput flat; tail latency grows")
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
    axC.set_title(f"(d) Short-circuit saves {C['pct_saved']:.0f}% work")
    axC.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
