# E2 — Throughput & Concurrency Scaling — Results

cores: 12

## Part A — CPU-bound fan-out: latency vs #rules (deterministic deberta path; median over reps)

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

## Part A-IO — I/O-bound fan-out: latency vs #judge nodes (network judge path; median over reps)

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
