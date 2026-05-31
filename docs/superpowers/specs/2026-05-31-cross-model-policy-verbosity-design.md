# Cross-Model Policy-Verbosity Ablation — Design

**Date:** 2026-05-31
**Builds on:** [2026-05-30-policy-verbosity-ablation-design.md](2026-05-30-policy-verbosity-ablation-design.md)
and its results ([2026-05-31-...-results.md](2026-05-31-policy-verbosity-ablation-results.md)).

## Research question

The single-model ablation (Llama 3.2) found injection-blocking is nearly
length-invariant while over-refusal is non-monotone in policy length (T1 worst,
T2 sweet spot, T3 regresses). Two open questions:

1. **Does the curve replicate across model families/sizes**, or do larger/more
   capable judges stop regressing at T3 (i.e., a capability×verbosity interaction)?
2. **What is the latency × accuracy × policy-length tradeoff?** Longer policies
   add prompt tokens to every judge call; that cost scales with model size. Which
   (model, rung) buys the most firewall quality per millisecond?

## Judge-model grid (5)

Chosen to span ~3B→~12B across three families for a size×family×latency spread.

| model (Ollama tag) | ~size | family | role | data source |
|---|---|---|---|---|
| `llama3.2:latest` | ~3B | Llama | small/fast baseline | **reuse** existing full dumps, sliced to the 300-attack subset |
| `qwen3:4b` | ~4B | Qwen | small | run (≈2.2 s/call, clean one-line verdict) |
| `llama3.1:8b` | ~8B | Llama | mid | run |
| `qwen3:8b` | ~8B | Qwen | mid | pull (~5 GB), then run |
| `gemma4:latest` | ~12B | Gemma | large/slow anchor | run (≈9.5 s/call — the latency extreme) |

## Fixed design (inherited, unchanged)

Same 16 conditions: 4 domains (marketing, healthcare, code, sql) × 4 verbosity
rungs (T0 terse → T3 full firewall), each a judge-only single-rule chain
(`rules/bench/policy_length.yaml`, `chains/bench/policy_length/`). Every run uses
`--no-cache` (the verdict cache key omits scope — mandatory), `--seed 42`, and the
same 50 in-domain benign prompts/domain (`corpora/policy_length/<domain>/benign/`).
Only the judge model varies, via `QFIRE_JUDGE_MODEL`.

## Attack subset (300, seeded) + llama3.2 reuse

To keep 4 new models tractable (~22k calls total vs ~63k at full scale), attacks
are sampled to **300 of the 929**, built **once** and shared by all models:

- `scripts/make_attack_subset.py`: seeded (seed 42) random selection of 300
  **sorted indices** from `corpora/eval/attacks/public_attacks.jsonl`; writes
  `corpora/policy_length/attacks_sample300/attacks_sample300.jsonl` in sorted-index
  order. Deterministic and reproducible.
- The 4 new models bench against this subset file → their dumps are in subset
  order.
- **llama3.2 reuse (no re-run):** the existing full dumps
  (`bench-out/policy_length/<domain>/dump/pl_<domain>_t*.jsonl`) are written in
  strict corpus order (attacks 0..928 then benign 0..49 — verified at
  `src/bench/mod.rs:141-165`). `make_attack_subset.py` also emits the chosen 300
  attack indices; a slicer picks those rows (+ all 50 benign rows, positions
  929..978) from each llama3.2 dump and writes
  `bench-out/policy_length_llama3.2/<domain>/dump/pl_<domain>_t*.jsonl`. Same 300
  prompts, identical order → apples-to-apples with the run models.
  - Latency for llama3.2 is taken from the **existing** `bench.json` (full-corpus
    p50/detector-ms; per-call latency is corpus-size-independent, so it is
    comparable; this is noted in the writeup).

## Latency & abstain — already instrumented

The bench records per-chain latency in `bench.json` (`mean_detector_ms`,
`p50_ms`, `p95_ms`, `p99_ms`). Because each condition is **judge-only**, detector
time ≈ the judge LLM call latency. No new instrumentation. The Qwen reasoning
failure mode (model never emits a parseable `IN/OUT SCOPE` line → abstain→allow)
is **not** separately instrumented: the dump's `score` (`judge.rs:139`,
`verdict==Block ? conf : 1−conf`) maps an abstain to ~0.7, colliding with the
weak-allow band, so abstain is not cleanly recoverable from `{is_attack, blocked,
score}`. Instead it surfaces directly as **depressed TPR** — an abstaining judge
fails to block attacks — which the accuracy panel already captures and the
writeup calls out where it appears.

## Harness

- `scripts/run_cross_model.sh`: for each model in the grid (except llama3.2),
  loop the 4 domains running `qfire bench` with the 4 rungs as `--chain` flags,
  `--attacks corpora/policy_length/attacks_sample300`, `--benign
  corpora/policy_length/<domain>/benign`, `--seed 42 --no-cache`, `--dump` and
  `--out` under `bench-out/policy_length_<model_slug>/<domain>/`, with
  `QFIRE_JUDGE_MODEL=<tag>` exported. Model slug = tag with `:`/`.` → `_`.
- Runs sequentially (one model loaded at a time); gemma4 is the long pole
  (~hours). Designed to run unattended in the background.

## Analysis & figure

`scripts/analyze_cross_model.py` reads every
`bench-out/policy_length_<model>/<domain>/dump/*.jsonl` (+ the llama3.2 slice),
computes per (model, domain, rung): TPR / TNR / over-refusal / J
(accuracy from the dumps), and reads per-call latency (`mean_detector_ms` per
chain) from each model's `bench.json` (llama3.2 from its existing full
`bench.json`). Latency lives only at `bench.json` (per model×domain×rung)
granularity — the dumps store only `{is_attack, blocked, score}` — so the pooled
per-(model, rung) latency is the **mean of `mean_detector_ms` across the 4
domains**. Emits `bench-out/policy_length_xmodel/results.md`:
pooled-per-model tables + the per-model length→J and length→latency series.

`scripts/plot_cross_model.py` → `paper/figs/policy_length_xmodel.png` (committed
even though `bench-out` is gitignored — figures live in `paper/figs/`), 3 panels:
- **(a) Accuracy:** pooled Youden's J vs rung, one line per model — does the T2
  sweet-spot / T3-regression hold across families and sizes?
- **(b) Latency:** pooled mean per-call ms vs rung, one line per model (likely log
  y) — how policy length costs latency, scaled by model size.
- **(c) Pareto:** pooled J vs mean per-call latency scatter over all (model, rung) — the
  quality-per-millisecond frontier; annotate the efficient points.

A model that abstains heavily (e.g. a reasoning model that never emits the
verdict line) shows up as a low-TPR, low-J line in panel (a) and is called out in
the writeup; it is not given a separate abstain column (see Latency & abstain).

Reuses `analyze_policy_length.metrics()` for the metric core (already unit-tested);
new pure helpers (subset selection, dump slicing, abstain rate) get their own
unit tests.

## Scope

In scope: the 5-model grid, 300-attack subset + llama3.2 reuse, latency+accuracy+
abstain analysis, cross-model findings doc + figure.

Out of scope (follow-ups): folding into the paper manuscript; testing the 23 GB
Qwen 3.6 reasoning judge (already covered by the separate judge-model ablation and
known to abstain/timeout); per-domain paper tables.

## Success criterion

A defensible cross-model answer to "does policy verbosity behave the same across
judge models, and what does length cost in latency" — a pooled length→J curve per
model, a length→latency curve per model, and a J-vs-latency Pareto (with any
abstaining model visible as a low-TPR line). Success = a trustworthy measurement,
whichever way the interaction goes.

## Artifacts

- `scripts/make_attack_subset.py` (+ test) → `corpora/policy_length/attacks_sample300/`
- llama3.2 sliced dumps → `bench-out/policy_length_llama3.2/`
- `scripts/run_cross_model.sh`
- `scripts/analyze_cross_model.py` (+ test), `scripts/plot_cross_model.py`
- `bench-out/policy_length_<model>/…` (run outputs, gitignored)
- `bench-out/policy_length_xmodel/results.md` + `paper/figs/policy_length_xmodel.png`
- `docs/superpowers/specs/2026-05-31-cross-model-policy-verbosity-results.md` (findings)
