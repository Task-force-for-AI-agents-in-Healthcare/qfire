# E2 — Throughput & Concurrency Scaling — Results

cores: 12

## Part A — latency vs #rules (median over reps)

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

## Part B — throughput vs in-flight concurrency (median over reps)

| load-concurrency N | QPS | p95 ms | p99 ms |
|---|---|---|---|
| 1 | 16.2 | 248.99 | 291.21 |
| 2 | 17.2 | 232.10 | 279.06 |
| 4 | 15.9 | 261.94 | 389.52 |
| 8 | 15.2 | 297.11 | 791.99 |
| 16 | 15.4 | 321.89 | 1555.51 |
| 32 | 15.5 | 602.50 | 3181.44 |
| 64 | 15.8 | 1123.37 | 6211.33 |

## Part C — cheap-before-expensive short-circuit

- detector work/prompt: gated 68.407 ms vs always 87.849 ms
- block-rate parity (recall not lost): gated 0.761 vs always 0.744
- **expensive detector work saved by short-circuit: 22.1%**
