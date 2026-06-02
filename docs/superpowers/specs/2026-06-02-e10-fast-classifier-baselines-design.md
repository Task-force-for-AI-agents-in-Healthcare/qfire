# E10 — Fast/compressed classifier baselines + latency–accuracy frontier — Design

**Date:** 2026-06-02
**Backlog:** [paper-strengthening backlog](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — pending user review before the implementation plan.

## Research question

E3 added a *strong* classifier (qualifire Sentinel, 431 ms p95) and a *slow* judge
(`llama3.1:8B`, up to 2 s). The comparison is missing the **fast/compressed** end of the
spectrum, which is exactly where QFIRE's ONNX DeBERTa sits and where the latency story is
won or lost. The new survey flags **hlyn-labs DeBERTa-70M** — an 83 MB INT8-ONNX injection
classifier reporting ~101 ms CPU and 91.68% accuracy, the optimized analogue of QFIRE's
embedded DeBERTa. E10 adds the fast-classifier tier and turns the scattered latency
numbers into one **latency-vs-F1 frontier** the reader can place QFIRE on.

## What's reused

- `scripts/baselines.py` (argparse, dir-aware, Wilson CI + latency percentiles) — the E3
  HF-transformers path. Candidates that load as standard `AutoModelForSequenceClassification`
  slot straight into `MODELS`.
- The two main corpora (public injection + QFIRE-HealthBench) and the E3 result JSONs /
  table-insertion path.
- The existing ROC/PR + per-call latency machinery for the frontier plot.

## New baselines (fast/compressed tier)

1. **hlyn-labs DeBERTa-70M** (`hlyn-labs/prompt-injection-judge-deberta-70m`) — primary
   add. **Caveat:** it ships as an **INT8 ONNX** graph, not a PyTorch `AutoModel`, so it
   needs an `onnxruntime` inference wrapper in `baselines.py` (a small `run_onnx_model`
   alongside `run_model`), or its PyTorch variant if one is published. The wrapper mirrors
   QFIRE's own ONNX path → also a faithful apples-to-apples latency comparison.
2. **PromptGuard-2 22M** (DeBERTa-xsmall variant) — the smaller LlamaFirewall classifier,
   the fast end of the Meta family (we already have the 86M).
3. *(optional)* **Qualifire Sentinel v2 (0.6B)** and/or **Vijil Dome (ModernBERT)** — if
   accessible and non-gated; rounds out the modern-classifier set.

All report the same metrics as the existing baselines on both corpora.

## Method

- Add a `run_onnx_model(name, repo/path, ...)` to `baselines.py` (onnxruntime + the
  model's tokenizer) returning the same metrics dict as `run_model`; register the
  ONNX-only models in an `ONNX_MODELS` list (parallel to `MODELS`/`OLLAMA_MODELS`),
  selectable via `--models`.
- Run all new baselines on public injection + QFIRE-HealthBench (seed 42), into the E3
  baseline JSONs; hand-insert rows into the head-to-head + HealthBench tables (and update
  `make_tables.py` labels for regen, as in E3).
- **Latency–accuracy frontier figure:** scatter every detector (lexical, DeBERTa-70M,
  PromptGuard-2 22M/86M, Sentinel, protectai DeBERTa, bare judge, QFIRE hybrid) as
  (p95 latency, F1) on public injection, with QFIRE highlighted — making "fast *and*
  accurate" visual and showing the Pareto frontier.

## Deliverables

- `baselines.py` ONNX path + `ONNX_MODELS`; a unit test for the wrapper's label mapping
  (verify which logit is the injection class — do **not** assume `prob[-1]`; read the
  model's `id2label`).
- Result JSONs; new fast-tier rows in both tables; a `paper/figs/latency_f1_frontier.png`
  + `scripts/plot_frontier.py`.
- Paper: a sentence/figure in §Head-to-head or §Latency placing QFIRE on the frontier;
  cite hlyn-labs + LlamaFirewall. Findings doc; backlog E10 ticked.

## Success criterion

The fast-classifier tier slotted into the head-to-head + HealthBench tables with matched
metrics + CIs, and a latency-vs-F1 frontier showing where QFIRE's hybrid sits relative to
the cheapest accurate classifiers. Expected: DeBERTa-70M is fast and competitive on public
injection but (like all classifiers) collapses on HealthBench recall — reinforcing the
central thesis from the cheap end; QFIRE buys the scope/PHI coverage at a bounded latency.

## Resolved decisions (user, 2026-06-02)
1. Full design spec now; plan when picked up.
2. Fast tier anchored on hlyn-labs DeBERTa-70M; PromptGuard-2 22M added; Sentinel-v2 /
   Vijil Dome optional (only if non-gated/accessible).

## Feasibility & risks
- **Easy–medium.** The wrinkle is the **ONNX/INT8 path** (the model isn't a plain
  `AutoModel`): needs an onnxruntime wrapper + correct tokenizer + verified label
  ordering. The biggest correctness trap is the injection-class index — **read
  `id2label`**, don't assume the last logit (the E3 Sentinel check is the template).
- **Gated/availability:** confirm hlyn-labs is downloadable (HF token); Sentinel-v2/Vijil
  may be gated → drop if inaccessible (no fabricated rows).
- **Latency comparability:** report all latencies on the same machine (the M2 Max in the
  reproducibility note); CPU threads pinned as in `baselines.py`.

## Open questions for the design review
1. Use hlyn-labs' INT8-ONNX graph directly (most faithful), or a PyTorch reload if
   available (simpler, but not the published 101 ms artifact)?
2. Include the optional Sentinel-v2 (0.6B) / Vijil Dome, or keep the tier to the two
   confirmed fast models?
3. Frontier figure on public injection only, or a second panel on HealthBench (to show
   the gap reopen at the cheap end)?
