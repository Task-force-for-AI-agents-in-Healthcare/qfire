#!/usr/bin/env python3
"""Aggregate the E2 throughput/scaling bench outputs into
bench-out/throughput/results.md (and a JSON the plotter reads).

Reads bench-out/throughput/{A_*,B_*,C_*}/bench.json. Part A: per K, median over
reps of wall (parallel) and summed (serial-equiv), at engine-concurrency 1 and 16.
Part B: per load-concurrency N, median QPS + p95/p99. Part C: % expensive-node
work saved by short-circuiting (from the dumps' score band / per-rule metrics).
"""
import glob
import json
import os
import re
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "bench-out/throughput")


def median(xs):
    return statistics.median(xs) if xs else 0.0


def speedup(summed, wall):
    return summed / wall if wall > 0 else 0.0


def pct_saved(gated, always):
    """Percent of expensive detector work saved by the short-circuit."""
    return 100.0 * (always - gated) / always if always else 0.0


def _overall(path):
    return json.load(open(path))["reports"][0]


def part_a():
    """{(K, ec): {'wall': median_ms, 'summed': median_ms}}"""
    rows = {}
    by = {}
    for d in glob.glob(os.path.join(ROOT, "A_scale_k*_ec*_r*")):
        m = re.search(r"A_scale_k(\d+)_ec(\d+)_r\d+$", d)
        if not m:
            continue
        k, ec = int(m.group(1)), int(m.group(2))
        o = _overall(os.path.join(d, "bench.json"))["overall"]
        by.setdefault((k, ec), {"wall": [], "summed": []})
        by[(k, ec)]["wall"].append(o["mean_wall_ms"])
        by[(k, ec)]["summed"].append(o["mean_detector_ms"])
    for key, v in by.items():
        rows[key] = {"wall": median(v["wall"]), "summed": median(v["summed"])}
    return rows


def part_a_io():
    """Judge fan-out (I/O-bound nodes): {(K, ec): {'wall', 'summed'}} median over reps.
    Unlike CPU-bound deberta, concurrent judge (network) calls overlap, so wall << summed."""
    by = {}
    for d in glob.glob(os.path.join(ROOT, "A_io_judge_k*_ec*_r*")):
        m = re.search(r"A_io_judge_k(\d+)_ec(\d+)_r\d+$", d)
        if not m:
            continue
        k, ec = int(m.group(1)), int(m.group(2))
        o = _overall(os.path.join(d, "bench.json"))["overall"]
        by.setdefault((k, ec), {"wall": [], "summed": []})
        by[(k, ec)]["wall"].append(o["mean_wall_ms"])
        by[(k, ec)]["summed"].append(o["mean_detector_ms"])
    return {key: {"wall": median(v["wall"]), "summed": median(v["summed"])}
            for key, v in by.items()}


def part_b():
    """{N: {'qps': median, 'p95': median, 'p99': median}}"""
    by = {}
    for d in glob.glob(os.path.join(ROOT, "B_n*_r*")):
        m = re.search(r"B_n(\d+)_r\d+$", d)
        if not m:
            continue
        n = int(m.group(1))
        r = _overall(os.path.join(d, "bench.json"))
        o = r["overall"]
        by.setdefault(n, {"qps": [], "p95": [], "p99": []})
        by[n]["qps"].append(r["throughput_qps"])
        by[n]["p95"].append(o["p95_ms"])
        by[n]["p99"].append(o["p99_ms"])
    return {n: {k: median(v) for k, v in d.items()} for n, d in by.items()}


def _detector_ms_and_block(run_dir):
    """(mean_detector_ms, block_rate) for a Part C chain run."""
    o = _overall(os.path.join(run_dir, "bench.json"))["overall"]
    return o["mean_detector_ms"], o["block_rate"]


def part_c():
    """Total detector work (mean_detector_ms) saved by gating deberta behind a
    cheap regex, on the attack corpus, with a recall/block-rate parity check."""
    g_ms, g_block = _detector_ms_and_block(os.path.join(ROOT, "C_sc_gated"))
    a_ms, a_block = _detector_ms_and_block(os.path.join(ROOT, "C_sc_always"))
    return {"gated_detector_ms": g_ms, "always_detector_ms": a_ms,
            "gated_block_rate": g_block, "always_block_rate": a_block,
            "pct_saved": pct_saved(g_ms, a_ms)}


def main():
    a, aio, b, c = part_a(), part_a_io(), part_b(), part_c()
    lines = ["# E2 — Throughput & Concurrency Scaling — Results", ""]
    mt = os.path.join(ROOT, "machine.txt")
    if os.path.exists(mt):
        lines.append(open(mt).read().strip()); lines.append("")
    lines += ["## Part A — CPU-bound fan-out: latency vs #rules (deterministic deberta path; median over reps)", "",
              "| K (rules) | engine-conc | wall ms (parallel) | summed ms (serial-equiv) | speedup |",
              "|---|---|---|---|---|"]
    for (k, ec) in sorted(a):
        v = a[(k, ec)]
        lines.append(f"| {k} | {ec} | {v['wall']:.2f} | {v['summed']:.2f} | "
                     f"{speedup(v['summed'], v['wall']):.2f}x |")
    if aio:
        lines += ["", "## Part A-IO — I/O-bound fan-out: latency vs #judge nodes (network judge path; median over reps)", "",
                  "| K (judge nodes) | engine-conc | wall ms (parallel) | summed ms (serial-equiv) | speedup |",
                  "|---|---|---|---|---|"]
        for (k, ec) in sorted(aio):
            v = aio[(k, ec)]
            lines.append(f"| {k} | {ec} | {v['wall']:.1f} | {v['summed']:.1f} | "
                         f"{speedup(v['summed'], v['wall']):.2f}x |")
    lines += ["", "## Part B — throughput vs in-flight concurrency (median over reps)", "",
              "| load-concurrency N | QPS | p95 ms | p99 ms |", "|---|---|---|---|"]
    for n in sorted(b):
        v = b[n]
        lines.append(f"| {n} | {v['qps']:.1f} | {v['p95']:.2f} | {v['p99']:.2f} |")
    lines += ["", "## Part C — cheap-before-expensive short-circuit", "",
              f"- detector work/prompt: gated {c['gated_detector_ms']:.3f} ms vs "
              f"always {c['always_detector_ms']:.3f} ms",
              f"- block-rate parity (recall not lost): gated {c['gated_block_rate']:.3f} "
              f"vs always {c['always_block_rate']:.3f}",
              f"- **expensive detector work saved by short-circuit: {c['pct_saved']:.1f}%**"]
    os.makedirs(ROOT, exist_ok=True)
    with open(os.path.join(ROOT, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(ROOT, "summary.json"), "w") as f:
        json.dump({"A": {f"{k}_{ec}": v for (k, ec), v in a.items()},
                   "A_IO": {f"{k}_{ec}": v for (k, ec), v in aio.items()},
                   "B": b, "C": c}, f, indent=1)
    print("wrote", os.path.join(ROOT, "results.md"))
    print("ANALYZE_THROUGHPUT_DONE")


if __name__ == "__main__":
    main()
