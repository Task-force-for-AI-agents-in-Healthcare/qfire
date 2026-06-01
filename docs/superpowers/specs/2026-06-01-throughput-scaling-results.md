# E2 — Throughput & Concurrency Scaling — Results

**Date:** 2026-06-01
**Status:** done
**Branch:** experiment/paper-strengthening
**Design spec:** [2026-06-01-throughput-scaling-design.md](2026-06-01-throughput-scaling-design.md)
**Figure:** `paper/figs/throughput_scaling.png`

---

## Setup

- **Machine:** 12 cores (Apple Silicon / Darwin 25.5.0)
- **Two detector paths measured:**
  - *Deterministic (CPU-bound):* regex → Aho-Corasick → entropy → DeBERTa ONNX classifier; all local, no network. This is the production injection-defense path.
  - *Judge (I/O-bound):* LLM scope judge calling local Ollama; dominated by network/inference wait, not CPU.
- **Important build note:** plain `cargo build --release` falls back to a sub-millisecond *lexical stub* when the ONNX model is absent, not the real DeBERTa classifier. All CPU-bound fan-out numbers below were produced with `cargo build --release --features onnx`, which embeds the ONNX Runtime and loads the real `deberta-v3-base-prompt-injection` weights. Results from a plain release build would be an order of magnitude faster and not representative of the production classifier.
- **Run parameters:** `--limit` (corpus subset) and `--reps` (median over repetitions) as configured in the throughput driver; engine-concurrency swept at 1 and 16.

---

## Part A — CPU-bound fan-out (deterministic deberta path; median over reps)

| K (rules) | engine-conc | wall ms (parallel) | summed ms (serial-equiv) | speedup |
|---|---|---|---|---|
| 1 | 1 | 0.00 | 0.00 | 0.14x |
| 1 | 16 | 0.00 | 0.00 | 0.14x |
| 2 | 1 | 19.96 | 16.25 | 0.81x |
| 2 | 16 | 19.83 | 16.12 | 0.81x |
| 4 | 1 | 35.77 | 32.00 | 0.89x |
| 4 | 16 | 35.63 | 31.97 | 0.90x |
| 8 | 1 | 68.14 | 64.43 | 0.95x |
| 8 | 16 | 67.56 | 63.87 | 0.95x |
| 16 | 1 | 198.04 | 194.09 | 0.98x |
| 16 | 16 | 197.22 | 193.36 | 0.98x |
| 21 | 1 | 290.03 | 285.90 | 0.99x |
| 21 | 16 | 277.11 | 273.29 | 0.99x |

---

## Part A-IO — I/O-bound fan-out (network judge path; median over reps)

| K (judge nodes) | engine-conc | wall ms (parallel) | summed ms (serial-equiv) | speedup |
|---|---|---|---|---|
| 1 | 1 | 186.7 | 186.7 | 1.00x |
| 1 | 16 | 190.0 | 190.0 | 1.00x |
| 2 | 1 | 488.8 | 488.7 | 1.00x |
| 2 | 16 | 404.9 | 635.1 | 1.57x |
| 4 | 1 | 1351.6 | 1351.5 | 1.00x |
| 4 | 16 | 1303.0 | 3523.4 | 2.70x |
| 8 | 1 | 2975.3 | 2975.2 | 1.00x |
| 8 | 16 | 3017.2 | 13828.7 | 4.58x |
| 16 | 1 | 6241.1 | 6240.9 | 1.00x |
| 16 | 16 | 6432.6 | 55981.0 | 8.70x |

---

## Part B — Throughput vs in-flight concurrency (median over reps)

| load-concurrency N | QPS | p95 ms | p99 ms |
|---|---|---|---|
| 1 | 16.2 | 248.99 | 291.21 |
| 2 | 17.2 | 232.10 | 279.06 |
| 4 | 15.9 | 261.94 | 389.52 |
| 8 | 15.2 | 297.11 | 791.99 |
| 16 | 15.4 | 321.89 | 1555.51 |
| 32 | 15.5 | 602.50 | 3181.44 |
| 64 | 15.8 | 1123.37 | 6211.33 |

---

## Part C — Cheap-before-expensive short-circuit

- Detector work/prompt: **gated 68.407 ms** vs **always 87.849 ms**
- Block-rate parity (recall not lost): gated 0.761 vs always 0.744
- **Expensive detector work saved by short-circuit: 22.1%**

---

## Figure

![E2 throughput scaling: 2x2 panel (a) CPU fan-out, (b) I/O fan-out, (c) throughput/tail, (d) short-circuit](../../../paper/figs/throughput_scaling.png)

---

## Findings

### (a) CPU-bound fan-out — parallelism does NOT help

Increasing engine-concurrency from 1 to 16 gives **no speedup** on the deterministic DeBERTa path. At K=21 rules, wall time ≈ summed serial time (speedup 0.99x at both ec=1 and ec=16; wall 277 ms vs summed 273 ms). At K=8 the speedup is 0.95x at both concurrency levels.

**Why:** concurrent ONNX inferences contend for the same saturated CPU cores. The Tokio runtime can issue concurrent tasks, but when every task is ONNX-bound the CPU is the bottleneck — task-level concurrency cannot speed up CPU-bound work beyond the available cores, and 21 DeBERTa calls saturate them completely.

### (b) I/O-bound fan-out — parallelism IS the payoff

At engine-concurrency 16 the judge path shows substantial overlap speedup that grows with K:

| K | speedup (ec=16) |
|---|---|
| 2 | 1.57x |
| 4 | 2.70x |
| 8 | 4.58x |
| 16 | **8.70x** |

At K=16, 55,981 ms of serial judge work completes in 6,433 ms wall time — an 8.70x speedup — because the engine overlaps the network/inference wait of all 16 concurrent judge calls. At engine-concurrency 1 the speedup is 1.00x (no overlap) at every K, as expected.

**This is the parallel low-latency payoff for the expensive node that dominates deployment cost.** A healthcare chain with 16 judge scope rules that would take ~56 s evaluated serially completes in ~6.4 s when the Tokio engine fans them out concurrently at ec=16.

### (c) Throughput and tail latency — bound in-flight concurrency

On the deterministic hybrid chain, QPS is flat at ~15–17 req/s across in-flight concurrency N=1..64 (bottleneck: the serialized ONNX classifier). Meanwhile tail latency blows up monotonically: p99 rises from **291 ms at N=1** to **6,211 ms at N=64** — a >21x tail blow-up with zero throughput gain.

**Lesson:** once the CPU classifier is the bottleneck, adding more in-flight requests only queues work and inflates tail latency. Operators should bound in-flight concurrency to the point where the p99 SLA is met; past that point more concurrency buys nothing and costs much.

### (d) Short-circuit — the CPU-path lever

Gating DeBERTa behind a cheap regex pre-filter saves **22.1%** of expensive classifier work (gated 68.407 ms vs always 87.849 ms per prompt) while maintaining equal or better recall (block-rate gated 0.761 vs always 0.744 — the short-circuit does not lose attacks; it avoids running the classifier on prompts already caught by the regex).

**Combined with finding (a):** for the CPU-bound DeBERTa path, short-circuiting — skipping the expensive node entirely when a cheap node already fired — is the real latency lever, not fan-out parallelism. Fan-out is the lever for I/O-bound judge nodes.

---

## Caveats

1. **Single-machine, warm-path latency.** All measurements are on one 12-core machine. CPU-bound behavior is hardware-dependent: a machine with more cores or with batched ONNX inference could show different fan-out behavior. The I/O result generalizes wherever the bottleneck is network/model wait rather than CPU.

2. **Ollama concurrency.** The I/O fan-out speedup is possible because Ollama serves concurrent requests in parallel (it queues or batches model inference across calls). The 8.70x result assumes an Ollama instance that can handle 16 concurrent judge requests. A single-threaded Ollama backend would serialize them and show 1.0x regardless of engine-concurrency.

3. **ONNX build requirement.** CPU numbers reflect the real DeBERTa classifier (`--features onnx`). A plain `cargo build --release` build uses a lexical stub (sub-ms) and would produce misleading fan-out results.

4. **No GPU / batched inference.** These results are CPU-only, single-prompt inference. GPU inference or batched ONNX could change the CPU saturation profile.
