# 04 · Benchmarking & reproducibility

**Goal:** replay attack and benign corpora through one or more chains and get
research-grade metrics — block rate, FPR/FNR, precision/recall/F1, AUC, and
latency percentiles — plus a paper-ready report with a reproducibility manifest.

**Time:** ~10 minutes (longer for big corpora). **Cost:** $0 (offline, local Ollama).

---

## 1. Regenerate the headline tables

The repo ships a one-liner that reproduces the headline benchmark:

```bash
make bench
```

This writes `bench-out/report.md` (plus `bench.json` and `bench.csv`). The
equivalent explicit invocation:

```bash
qfire bench --chain default --chain hipaa_phi \
    --attack-in-prompt --seed 42 --out bench-out
```

What the flags mean:

| Flag | Effect |
|---|---|
| `--chain` (repeatable) | one or more chains to benchmark side-by-side |
| `--attacks` / `--benign` | corpus directories (default `corpora/attacks`, `corpora/benign`) |
| `--attack-in-prompt` | also test **camouflaged** injections hidden inside benign prompts (PyRIT-style) |
| `--seed` | deterministic shuffling for reproducible runs (default `42`) |
| `--out` | output directory for `bench.json` / `bench.csv` / `report.md` |
| `--limit N` | cap prompts per corpus (`0` = all) — handy for a quick smoke run |

## 2. Read the results

`qfire bench` replays the attack corpus and the paired benign corpus through each
chain and computes, **per rule and per chain**:

- block rate and successful-injection rate
- FPR / FNR, precision / recall / F1, AUC
- latency p50 / p95 / p99 and firewall overhead

`report.md` is written for direct inclusion in a paper. **Attack-in-prompt**
results are reported *separately* from naked-attack resistance, so you can see
both raw detection and camouflage robustness.

```bash
open bench-out/report.md        # or: less bench-out/report.md
column -s, -t < bench-out/bench.csv | less -S
```

## 3. Honest latency

The verdict cache (keyed by prompt hash + node version) makes repeated prompts
fast — great in production, misleading in a latency benchmark. For un-warmed,
honest per-chain latency:

```bash
qfire bench --chain default --no-cache --out bench-out-cold
```

Tune engine parallelism and simulate concurrent load:

```bash
qfire bench --chain default \
  --engine-concurrency 16 \   # max detector nodes running at once
  --load-concurrency 8        # prompt evaluations in flight (in-process load test)
```

## 4. Paired statistics (McNemar, bootstrap CIs)

To compare two chains rigorously, dump per-prompt predictions and run paired
tests:

```bash
qfire bench --chain default --chain injection_ordered \
  --dump preds/ --out bench-out
# → preds/default.jsonl, preds/injection_ordered.jsonl  (one row per prompt)
```

Each file has one JSON row per prompt (prediction + label), which feeds McNemar's
test and bootstrap confidence intervals — the apples-to-apples way to claim chain
A beats chain B.

## 5. Bring your own corpus

Small attack/benign snapshots ship in `corpora/`. Import the full
[garak](https://github.com/NVIDIA/garak) or
[PyRIT](https://github.com/microsoft/PyRIT) corpora (run as external Python
harnesses — never runtime dependencies of the proxy hot path):

```bash
# import a garak report into the corpus
qfire attack import garak-report.jsonl --format garak --out corpora/attacks/garak.jsonl

# mutate benign prompts into attack-in-prompt (camouflaged) variants
qfire attack mutate corpora/benign/benign_samples.txt --out corpora/attacks/aip.jsonl
```

Then point `bench` at your directories:

```bash
qfire bench --chain default --attacks corpora/attacks --benign corpora/benign --out bench-out
```

## 6. Reproducibility manifest

Every artifact embeds the exact **seed, model, and rule/chain/corpus versions**.
That means `make bench` reproduces the headline numbers on another machine with
no paid keys, and any `bench.json` is self-describing — you can tell precisely
which detector versions produced a row.

---

### What you learned

- `make bench` reproduces the headline tables end-to-end, offline.
- Report attack-in-prompt robustness *separately* from naked-attack resistance.
- `--no-cache` for honest latency; `--dump` for paired McNemar / bootstrap stats.
- Import garak/PyRIT corpora via `qfire attack import` without touching the hot path.

**Next:** a domain where generic detectors collapse → [05 · Healthcare / PHI guardrails](05-healthcare-phi-guardrails.md)
