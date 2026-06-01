# E2 — Throughput & Concurrency Scaling — Design

**Date:** 2026-06-01
**Backlog:** [paper-strengthening E2](2026-06-01-paper-strengthening-experiments-backlog.md)

## Research question

QFIRE's contribution (ii) is an *asynchronous detector graph* (Tokio, rules and
typed detector nodes fanned out via `join_all` under a semaphore, with
cheap-before-expensive short-circuiting). The paper currently evidences it only
with **per-call** p50/p95/p99 latency. This experiment measures the actual
parallelism payoff on three axes:

- **A. Rule fan-out (intra-request):** does chain latency stay ≈ the slowest node
  as the number of rules grows, rather than the sum of node times?
- **B. Inter-request throughput:** does throughput (QPS) scale with in-flight
  concurrency up to the core/semaphore limit, with bounded tail latency?
- **C. Cheap-before-expensive:** does short-circuiting a cheap lexical node before
  an expensive classifier actually save expensive work?

All on the **deterministic** detector path (regex / aho / entropy / deberta) — no
LLM judge — so the architecture signal is not swamped by multi-second model calls.

## What already exists (reused, not rebuilt)

- The engine fans rules out with `join_all` (`engine.rs:171`) and nodes within a
  rule (`engine.rs:390`), bounded by a `Semaphore` (default 16;
  `Engine::with_concurrency(n)`, `engine.rs:107`).
- The bench records, per prompt, BOTH `wall_clock_ms` (parallel wall time) and
  `summed_detector_ms` (sum of node times = serial-equivalent cost)
  (`engine.rs:172,176`; surfaced in `bench/mod.rs:243-244`) — so Part A needs no
  new instrumentation.
- 130 rules exist (101 regex, 15 deberta, 3 aho, 3 entropy) to compose large
  deterministic chains.
- `qfire bench` replays a corpus **sequentially** today — Part B adds a concurrent
  load mode.

## Code changes (Rust)

1. **`--engine-concurrency N`** flag on `bench` → calls `Engine::with_concurrency(N)`
   (default keep 16). Lets Part A contrast forced-serial (N=1) vs parallel.
2. **`--load-concurrency N`** flag on `bench` → switches the replay loop from
   sequential to **N evaluations in flight** (`futures::stream::buffer_unordered`
   or `JoinSet`), in-process (no HTTP, no provider forward). When set, the bench
   also reports **throughput** (prompts ÷ total wall seconds = QPS) and the same
   p50/p95/p99 per-request latencies. Default 1 = today's sequential behavior
   (back-compatible).
3. (No new metric types — reuse `Metrics`; add a `throughput_qps` field + total
   wall to the manifest/report.)

The replay-loop refactor is the one unit-testable seam: a `run_corpus(engine,
chain, prompts, load_concurrency)` that returns the samples + total wall. Unit
test asserts **correctness, not timing** (flaky): with a deterministic stub
detector, the returned sample count equals the prompt count and the per-prompt
verdicts are identical for `load_concurrency` 1 vs 8 (concurrency must not change
results). The speedup itself is an integration observation reported by the run,
not a unit-test assertion.

## Part A — rule-fanout harness

- `scripts/gen_scaling_chains.py`: emit expression chains referencing
  `K ∈ {1,2,4,8,16,32,64,96}` distinct deterministic rules (regex-family, drawn
  deterministically from the rule library), as
  `chains/bench/scaling/scale_k<K>.yaml` (one chain per file, expression
  `r1 AND r2 AND … AND rK`).
- Run `qfire bench` over a fixed benign corpus (benign so rules mostly *don't*
  block → every node actually runs, exercising full fan-out; a blocking prompt
  would short-circuit and hide the fan-out). Record per-prompt `wall_clock_ms` and
  `summed_detector_ms` for each K, at `--engine-concurrency` 1 (serial) and 16
  (parallel). Several repetitions + warm-up; report medians.
- **Outputs:** median wall and summed vs K; parallel speedup (summed/wall) vs K.

## Part B — throughput harness

- Run `qfire bench --load-concurrency N` for `N ∈ {1,2,4,8,16,32,64}` on a fixed
  deterministic chain (the QFIRE hybrid-style deterministic chain) over the attack
  corpus (attacks → BLOCK short-circuits, no forward — pure firewall throughput).
- **Outputs:** QPS vs N (expect rise then plateau near the core count / semaphore
  cap) and p95/p99 vs N (tail under load). Report the machine core count.

## Part C — cheap-before-expensive

- Two chains over the same prompts: (i) `regex → deberta` with
  `stop_on_first_block` (cheap gates expensive); (ii) deberta-only (always runs).
- Measure the fraction of prompts that reach the deberta node (from per-rule node
  traces / dump) and total `summed_detector_ms`, chain (i) vs (ii).
- **Output:** "short-circuit fires the expensive classifier on only X% of prompts,
  cutting total detector work by Y%."

## Analysis & figure

- `scripts/analyze_throughput.py`: read the Part A/B/C bench JSONs, compute the
  medians/QPS/short-circuit savings, write
  `bench-out/throughput/results.md`.
- `scripts/plot_throughput.py` → `paper/figs/throughput_scaling.png`, 3 panels:
  (a) latency vs #rules (wall parallel vs summed serial; log-x), (b) QPS vs
  in-flight concurrency (+ tail latency overlay or a 4th panel), (c) short-circuit
  work saved. Pure-Python helpers (QPS, percentile, median-over-reps) unit-tested.

## Deliverables

- Rust: `--engine-concurrency`, `--load-concurrency` flags + `run_corpus` seam (+ tests).
- `scripts/gen_scaling_chains.py`, `chains/bench/scaling/*.yaml`.
- `scripts/run_throughput.sh` (drives Parts A/B/C), `scripts/analyze_throughput.py`
  (+ test), `scripts/plot_throughput.py`.
- `bench-out/throughput/…` (gitignored), `paper/figs/throughput_scaling.png`.
- Findings doc + paper subsection (System Design §async detector graph; mirrored in
  `PAPER.md`).

## Success criterion

Measured curves showing (A) wall-time grows far slower than summed as rules scale
(parallel speedup rising with K), (B) QPS scales with concurrency to a plateau with
controlled tail latency, and (C) short-circuiting measurably cuts expensive-node
work — turning the "parallel, low-latency" claim from per-call latency into a
scaling result. Success = a trustworthy measurement regardless of the exact curve.

## Caveats (to state in the writeup)

- Single-machine, warm measurements; absolute numbers depend on hardware/core count
  (reported), not portable benchmarks — the *shapes/ratios* are the result.
- Deterministic path only; a judge-bearing chain is latency-dominated by the model
  (already covered by the judge-model ablation), out of scope here.
- In-process load (no HTTP/axum, no provider forward) isolates engine throughput;
  an optional `qfire serve` HTTP spot-check (all-block attack traffic) can confirm
  proxy overhead is small but is not the primary measurement.

## Scope

In: Parts A, B, C as above; the two CLI flags + load seam; analysis, figure,
findings, paper subsection. Out: HTTP/axum load testing as a primary axis;
judge-path scaling; distributed/multi-process throughput.
